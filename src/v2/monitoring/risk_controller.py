# src/v2/monitoring/risk_controller.py
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
    ensure_dir,
)

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.logger import get_logger  # type: ignore


logger = get_logger("risk_controller")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(get_data_dir())
TRADING_DIR = DATA_DIR / "trading"
ANALYSIS_DIR = DATA_DIR / "analysis"
TELEMETRY_DIR = DATA_DIR / "telemetry"
STATE_DIR = DATA_DIR / "state"

RISK_LIMITS_FILE = TRADING_DIR / "risk_limits.json"


# ---------------------------------------------------------------------------
# Defaults / thresholds (env-overridable)
# ---------------------------------------------------------------------------

DEFAULT_MAX_POSITIONS = int(os.getenv("NSC_MAX_POSITIONS_DEFAULT", "50"))

# Drawdown thresholds (daily)
MAX_DD_SOFT = float(os.getenv("NSC_MAX_DAILY_DD_SOFT", "0.05"))  # 5%
MAX_DD_HARD = float(os.getenv("NSC_MAX_DAILY_DD_HARD", "0.10"))  # 10%

# Risk Engine score thresholds
RISK_SCORE_OK = float(os.getenv("NSC_RISK_SCORE_OK", "70"))       # >= 70 => ok
RISK_SCORE_CAUTION = float(os.getenv("NSC_RISK_SCORE_CAUTION", "55"))  # 55-69 => caution
RISK_SCORE_DANGER = float(os.getenv("NSC_RISK_SCORE_DANGER", "45"))    # 45-54 => danger
# < 45 => emergency

# Size factors by mode
SIZE_NORMAL = float(os.getenv("NSC_SIZE_FACTOR_NORMAL", "1.0"))
SIZE_REDUCED = float(os.getenv("NSC_SIZE_FACTOR_REDUCED", "0.5"))
SIZE_EMERGENCY = float(os.getenv("NSC_SIZE_FACTOR_EMERGENCY", "0.0"))

# Positions by mode
MAX_POS_NORMAL = int(os.getenv("NSC_MAX_POSITIONS_NORMAL", str(DEFAULT_MAX_POSITIONS)))
MAX_POS_REDUCED = int(os.getenv("NSC_MAX_POSITIONS_REDUCED", str(max(1, DEFAULT_MAX_POSITIONS // 2))))
MAX_POS_EMERGENCY = int(os.getenv("NSC_MAX_POSITIONS_EMERGENCY", "0"))

# Trailing stop ATR multiplier hint (position_manager will clamp anyway)
TRAIL_ATR_NORMAL = float(os.getenv("NSC_TRAILING_ATR_MULT_NORMAL", "2.0"))
TRAIL_ATR_REDUCED = float(os.getenv("NSC_TRAILING_ATR_MULT_REDUCED", "1.75"))
TRAIL_ATR_EMERGENCY = float(os.getenv("NSC_TRAILING_ATR_MULT_EMERGENCY", "1.75"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load(path: Path, default: Any = None) -> Any:
    return load_json_file(path, default=default)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_str(x: Any, default: str = "") -> str:
    try:
        if x is None:
            return default
        return str(x)
    except Exception:
        return default


def _safe_bool(x: Any, default: bool = False) -> bool:
    try:
        if x is None:
            return default
        return bool(x)
    except Exception:
        return default


def _extract_market_regime(market_regime: Dict[str, Any]) -> Tuple[str, str]:
    """
    market_regime_detector.json:
      { "regime": "neutral", "risk_mode": "reduced" }
    """
    regime = _safe_str(market_regime.get("regime"), "neutral")
    risk_mode = _safe_str(market_regime.get("risk_mode"), "normal")
    return regime, risk_mode


def _extract_kill_switch(kill_switch: Dict[str, Any]) -> Dict[str, Any]:
    """
    kill_switch.json expected fields (best-effort):
      enabled, mode, hard_block, soft_block
    """
    enabled = _safe_bool(kill_switch.get("enabled"), False)
    mode = _safe_str(kill_switch.get("mode"), "soft")
    hard_block = _safe_bool(kill_switch.get("hard_block"), False) or mode in ("hard", "hard_block")
    soft_block = _safe_bool(kill_switch.get("soft_block"), False) or mode in ("soft", "soft_block")
    return {
        "enabled": enabled,
        "mode": mode,
        "hard_block": hard_block,
        "soft_block": soft_block,
    }


def _extract_protocol_mode(production_protocol: Dict[str, Any]) -> str:
    # telemetry/production_protocol.json
    return _safe_str(production_protocol.get("mode"), "normal")


def _extract_backpressure_mode(backpressure: Dict[str, Any]) -> str:
    # telemetry/backpressure_state.json
    return _safe_str(backpressure.get("mode"), "normal")


def _extract_daily_drawdown(daily_feedback: Dict[str, Any]) -> float:
    """
    daily_trading_feedback.json (si présent)
      daily_drawdown_pct (0-1)
    """
    dd = daily_feedback.get("daily_drawdown_pct")
    if dd is None:
        # compat: certains modules mettent un champ "daily_drawdown"
        dd = daily_feedback.get("daily_drawdown", 0.0)
    return _safe_float(dd, 0.0)


def _extract_risk_engine_score(risk_engine: Dict[str, Any]) -> Tuple[float, str]:
    """
    risk_engine_pro.json:
      { "score": 55.0, "flag": "caution" }
    """
    score = _safe_float(risk_engine.get("score"), 50.0)
    flag = _safe_str(risk_engine.get("flag"), "neutral")
    return score, flag


@dataclass
class RiskPolicy:
    mode: str              # normal / reduced / emergency
    risk_on_off: str        # on / off
    size_factor: float
    max_positions: int
    trailing_atr_mult: float


def _policy_from_inputs(
    market_risk_mode: str,
    risk_engine_score: float,
    risk_engine_flag: str,
    prod_mode: str,
    backpressure_mode: str,
    daily_dd: float,
    kill: Dict[str, Any],
) -> Tuple[RiskPolicy, List[str]]:
    """
    Décision globale.
    IMPORTANT: pas de dépendance à governance_engine_pro pour éviter la boucle.
    """
    reasons: List[str] = []

    # base: normal
    mode = "normal"
    risk_on_off = "on"
    size_factor = SIZE_NORMAL
    max_positions = MAX_POS_NORMAL
    trailing = TRAIL_ATR_NORMAL

    # --- 1) Protocole prod / backpressure (hard gating) ---
    if prod_mode == "emergency":
        mode = "emergency"
        risk_on_off = "off"
        size_factor = SIZE_EMERGENCY
        max_positions = MAX_POS_EMERGENCY
        trailing = TRAIL_ATR_EMERGENCY
        reasons.append("production_protocol_mode=emergency")
        # emergency is terminal
        return RiskPolicy(mode, risk_on_off, size_factor, max_positions, trailing), reasons

    if backpressure_mode == "emergency":
        mode = "emergency"
        risk_on_off = "off"
        size_factor = SIZE_EMERGENCY
        max_positions = MAX_POS_EMERGENCY
        trailing = TRAIL_ATR_EMERGENCY
        reasons.append("backpressure_mode=emergency")
        return RiskPolicy(mode, risk_on_off, size_factor, max_positions, trailing), reasons

    if prod_mode == "degraded":
        # degrade => reduced
        mode = "reduced"
        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append("production_protocol_mode=degraded")

    if backpressure_mode == "degraded":
        mode = "reduced"
        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append("backpressure_mode=degraded")

    # --- 2) Drawdown (hard gating) ---
    if daily_dd >= MAX_DD_HARD:
        mode = "emergency"
        risk_on_off = "off"
        size_factor = SIZE_EMERGENCY
        max_positions = MAX_POS_EMERGENCY
        trailing = TRAIL_ATR_EMERGENCY
        reasons.append(f"daily_drawdown_pct={daily_dd:.2%} >= hard={MAX_DD_HARD:.2%}")
        return RiskPolicy(mode, risk_on_off, size_factor, max_positions, trailing), reasons

    if daily_dd >= MAX_DD_SOFT:
        mode = "reduced"
        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append(f"daily_drawdown_pct={daily_dd:.2%} >= soft={MAX_DD_SOFT:.2%}")

    # --- 3) Kill switch (hard/soft gating) ---
    if kill.get("enabled") and kill.get("hard_block"):
        mode = "emergency"
        risk_on_off = "off"
        size_factor = SIZE_EMERGENCY
        max_positions = MAX_POS_EMERGENCY
        trailing = TRAIL_ATR_EMERGENCY
        reasons.append("kill_switch=hard_block")
        return RiskPolicy(mode, risk_on_off, size_factor, max_positions, trailing), reasons

    if kill.get("enabled") and kill.get("soft_block"):
        mode = "reduced"
        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append("kill_switch=soft_block")

    # --- 4) Market regime risk_mode (from market_regime_detector) ---
    if market_risk_mode == "reduced":
        mode = "reduced"
        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append("market_risk_mode=reduced")

    # --- 5) Risk engine score/flag ---
    # Score-based override
    if risk_engine_score < RISK_SCORE_DANGER:
        mode = "emergency"
        risk_on_off = "off"
        size_factor = SIZE_EMERGENCY
        max_positions = MAX_POS_EMERGENCY
        trailing = TRAIL_ATR_EMERGENCY
        reasons.append(f"risk_engine_score={risk_engine_score:.2f} (<{RISK_SCORE_DANGER:.2f})")
        return RiskPolicy(mode, risk_on_off, size_factor, max_positions, trailing), reasons

    if risk_engine_score < RISK_SCORE_CAUTION:
        # danger zone => reduced
        mode = "reduced"
        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append(f"risk_engine_score={risk_engine_score:.2f} flag={risk_engine_flag}")

    # Also honor explicit flag (best-effort)
    if risk_engine_flag in ("danger", "emergency"):
        mode = "reduced" if risk_engine_flag == "danger" else "emergency"
        if mode == "emergency":
            risk_on_off = "off"
            size_factor = SIZE_EMERGENCY
            max_positions = MAX_POS_EMERGENCY
            trailing = TRAIL_ATR_EMERGENCY
            reasons.append("risk_engine_flag=emergency")
            return RiskPolicy(mode, risk_on_off, size_factor, max_positions, trailing), reasons

        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append("risk_engine_flag=danger")

    if risk_engine_flag == "caution":
        mode = "reduced"
        size_factor = min(size_factor, SIZE_REDUCED)
        max_positions = min(max_positions, MAX_POS_REDUCED)
        trailing = TRAIL_ATR_REDUCED
        reasons.append("risk_engine_flag=caution")

    # --- 6) Final policy: trading on/off ---
    if mode == "emergency":
        risk_on_off = "off"
        size_factor = SIZE_EMERGENCY
        max_positions = MAX_POS_EMERGENCY
        trailing = TRAIL_ATR_EMERGENCY
        reasons.append("policy_mode=emergency => risk_on_off=off")

    return RiskPolicy(mode, risk_on_off, size_factor, max_positions, trailing), reasons


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_risk_limits(data_dir: Path) -> Dict[str, Any]:
    ensure_dir(str(TRADING_DIR))

    env = os.getenv("NSC_ENV", "PREPROD")

    # Inputs
    market_regime = _load(ANALYSIS_DIR / "market_regime_detector.json", default={})
    market_conditions = _load(ANALYSIS_DIR / "market_conditions_engine_pro.json", default={})
    coherence = _load(ANALYSIS_DIR / "market_coherence_engine_pro.json", default={})
    volatility_state = _load(ANALYSIS_DIR / "volatility_state_machine_pro.json", default={})

    risk_engine = _load(ANALYSIS_DIR / "risk_engine_pro.json", default={})
    production_protocol = _load(TELEMETRY_DIR / "production_protocol.json", default={})
    backpressure = _load(TELEMETRY_DIR / "backpressure_state.json", default={})

    kill_switch = _load(TRADING_DIR / "kill_switch.json", default={})
    daily_feedback = _load(TRADING_DIR / "daily_trading_feedback.json", default={})

    regime, market_risk_mode = _extract_market_regime(market_regime if isinstance(market_regime, dict) else {})
    risk_engine_score, risk_engine_flag = _extract_risk_engine_score(risk_engine if isinstance(risk_engine, dict) else {})
    prod_mode = _extract_protocol_mode(production_protocol if isinstance(production_protocol, dict) else {})
    bp_mode = _extract_backpressure_mode(backpressure if isinstance(backpressure, dict) else {})
    kill = _extract_kill_switch(kill_switch if isinstance(kill_switch, dict) else {})
    daily_dd = _extract_daily_drawdown(daily_feedback if isinstance(daily_feedback, dict) else {})

    # Policy decision
    policy, policy_reasons = _policy_from_inputs(
        market_risk_mode=market_risk_mode,
        risk_engine_score=risk_engine_score,
        risk_engine_flag=risk_engine_flag,
        prod_mode=prod_mode,
        backpressure_mode=bp_mode,
        daily_dd=daily_dd,
        kill=kill,
    )

    # Compose output (keep your fields)
    out: Dict[str, Any] = {
        "updated_at": _utc_now(),
        "risk_mode": policy.mode,
        "risk_on_off": policy.risk_on_off,

        # compat (some modules used this)
        "risk_on": (policy.risk_on_off == "on"),

        "size_factor": round(policy.size_factor, 4),
        "trailing_atr_mult": float(policy.trailing_atr_mult),

        "max_daily_drawdown_pct_soft": float(MAX_DD_SOFT),
        "max_daily_drawdown_pct_hard": float(MAX_DD_HARD),
        "daily_drawdown_pct": float(daily_dd),

        "market_regime": regime,

        # best-effort passthroughs (if present)
        "market_microstructure_regime": _safe_str(market_regime.get("microstructure_regime"), "normal")
        if isinstance(market_regime, dict) else "normal",
        "market_orderflow_regime": _safe_str(market_regime.get("orderflow_regime"), "normal")
        if isinstance(market_regime, dict) else "normal",

        # legacy / UI hints
        "risk_console_flag": "caution" if policy.mode != "normal" else "ok",

        "kill_switch": kill,

        "reasons": [
            f"market_regime={regime}",
            f"market_risk_mode={market_risk_mode}",
            f"risk_engine_score={risk_engine_score:.2f} flag={risk_engine_flag}",
            f"production_protocol_mode={prod_mode}",
            f"backpressure_mode={bp_mode}",
            f"daily_drawdown_pct={daily_dd:.2%} (soft={MAX_DD_SOFT:.2%}, hard={MAX_DD_HARD:.2%})",
            ("Kill-switch disabled." if not kill.get("enabled") else f"Kill-switch enabled (mode={kill.get('mode')})."),
            *policy_reasons,
        ],

        # this "mode" was in your file too
        "mode": "emergency" if policy.mode == "emergency" else policy.mode,

        "max_positions": int(policy.max_positions),
        "env": env,

        # helpful debug inputs (safe & small)
        "inputs": {
            "market_conditions_score": _safe_float((market_conditions or {}).get("score"), 50.0)
            if isinstance(market_conditions, dict) else 50.0,
            "coherence_score": _safe_float((coherence or {}).get("score"), 50.0)
            if isinstance(coherence, dict) else 50.0,
            "volatility_score": _safe_float((volatility_state or {}).get("score"), 50.0)
            if isinstance(volatility_state, dict) else 50.0,
        },
    }

    return out


def main() -> None:
    env = os.getenv("NSC_ENV", "PREPROD")
    logger.info("[risk_controller] DATA_DIR=%s env=%s", str(DATA_DIR), env)

    ensure_dir(str(TRADING_DIR))

    out = build_risk_limits(DATA_DIR)

    save_json_file(RISK_LIMITS_FILE, out)
    logger.info(
        "[risk_controller] risk_limits.json sauvegardé (%s) – mode=%s, risk_on_off=%s, size_factor=%.2f, max_positions=%s",
        str(RISK_LIMITS_FILE),
        out.get("mode"),
        out.get("risk_on_off"),
        _safe_float(out.get("size_factor"), 0.0),
        out.get("max_positions"),
    )


if __name__ == "__main__":
    main()
