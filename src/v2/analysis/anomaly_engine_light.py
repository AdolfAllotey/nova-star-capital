"""
anomaly_engine_light.py
-----------------------

Brique "Anomaly Engine" light – Saison 1 (hedge fund light).

But :
- Scanner les principaux outputs (signaux, risques, gouvernance, émotions)
- Identifier des situations anormales / contradictoires
- Produire un JSON structuré pour la gouvernance et l'UI

Entrées :
- data/analysis/signal_candidates.json
- data/analysis/momentum_scores.json
- data/analysis/liquidity_risk_overview.json
- data/analysis/mm_withdrawal_overview.json
- data/analysis/hype_cycle_overview.json
- data/analysis/emotional_regime.json
- data/reports/daily_trading_feedback.json
- data/reports/trading_checklist.json

Sortie :
- data/analysis/anomaly_overview.json

Format :
{
  "timestamp": "...",
  "summary": {
    "nb_anomalies": 3,
    "nb_critical": 1,
    "nb_warning": 2
  },
  "anomalies": [
    {
      "id": "ENTER_WITH_LIQUIDITY_BLOCK",
      "severity": "critical",
      "category": "liquidity",
      "symbol": "bitcoin",
      "description": "Signal enter_long alors que avoid_liquidity_pool=True",
      "details": { ... }
    },
    ...
  ]
}
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("anomaly_engine_light")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"
REPORTS_DIR = DATA_DIR / "reports"

ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

SIGNAL_CANDIDATES_FILE = ANALYSIS_DIR / "signal_candidates.json"
MOMENTUM_FILE = ANALYSIS_DIR / "momentum_scores.json"
LIQUIDITY_FILE = ANALYSIS_DIR / "liquidity_risk_overview.json"
MM_WITHDRAWAL_FILE = ANALYSIS_DIR / "mm_withdrawal_overview.json"
HYPE_FILE = ANALYSIS_DIR / "hype_cycle_overview.json"
EMOTIONAL_FILE = ANALYSIS_DIR / "emotional_regime.json"

DAILY_FEEDBACK_FILE = REPORTS_DIR / "daily_trading_feedback.json"
CHECKLIST_FILE = REPORTS_DIR / "trading_checklist.json"

OUTPUT_FILE = ANALYSIS_DIR / "anomaly_overview.json"

logger.info("[anomaly_engine_light] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default: Any = None) -> Any:
    return load_json_file(str(path), default=default)


def _save_json(path: Path, data: Any) -> None:
    save_json_file(str(path), data)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_bool(x: Any, default: bool = False) -> bool:
    if isinstance(x, bool):
        return x
    if x in ("true", "True", "1"):
        return True
    if x in ("false", "False", "0"):
        return False
    return default


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Anomaly:
    id: str
    severity: str  # "critical" / "warning" / "info"
    category: str
    description: str
    symbol: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Load inputs
# ---------------------------------------------------------------------------

def _load_signal_candidates() -> List[Dict[str, Any]]:
    data = _load_json(SIGNAL_CANDIDATES_FILE, default=[])
    if not isinstance(data, list):
        logger.warning("[anomaly_engine_light] signal_candidates.json invalide.")
        return []
    return data


def _load_dict_file(path: Path) -> Dict[str, Any]:
    data = _load_json(path, default={})
    if not isinstance(data, dict):
        return {}
    return data


def _load_daily_feedback() -> Dict[str, Any]:
    data = _load_json(DAILY_FEEDBACK_FILE, default={})
    if not isinstance(data, dict):
        return {}
    return data


def _load_checklist() -> Dict[str, Any]:
    data = _load_json(CHECKLIST_FILE, default={})
    if not isinstance(data, dict):
        return {}
    return data


def _load_emotional_regime() -> Dict[str, Any]:
    data = _load_json(EMOTIONAL_FILE, default={})
    if not isinstance(data, dict):
        return {}
    return data


# ---------------------------------------------------------------------------
# Per-asset anomalies
# ---------------------------------------------------------------------------

def _check_per_asset_anomalies(
    signals: List[Dict[str, Any]],
    liquidity: Dict[str, Any],
    mm_withdrawal: Dict[str, Any],
    hype: Dict[str, Any],
) -> List[Anomaly]:
    anomalies: List[Anomaly] = []

    for s in signals:
        if not isinstance(s, dict):
            continue

        symbol = s.get("symbol")
        action = s.get("action")
        inputs = s.get("inputs") or {}

        if not symbol or not action:
            continue

        symbol_str = str(symbol)

        # Liquidity
        liq_entry = liquidity.get(symbol_str) if isinstance(liquidity, dict) else None
        liq_score = _safe_float(
            liq_entry.get("liquidity_risk_score") if isinstance(liq_entry, dict) else None,
            0.0,
        )
        avoid_liquidity_pool = _safe_bool(
            liq_entry.get("avoid_liquidity_pool") if isinstance(liq_entry, dict) else False,
            False,
        )

        # MM withdrawal
        mm_entry = mm_withdrawal.get(symbol_str) if isinstance(mm_withdrawal, dict) else None
        mm_detected = _safe_bool(
            mm_entry.get("withdrawal_detected") if isinstance(mm_entry, dict) else False,
            False,
        )
        mm_score = _safe_float(
            mm_entry.get("mm_withdrawal_score") if isinstance(mm_entry, dict) else None,
            0.0,
        )

        # Hype
        hype_entry = hype.get(symbol_str) if isinstance(hype, dict) else None
        hype_block = _safe_bool(
            hype_entry.get("hype_block_entry") if isinstance(hype_entry, dict) else False,
            False,
        )
        hype_score = _safe_float(
            hype_entry.get("hype_score") if isinstance(hype_entry, dict) else None,
            0.0,
        )
        hype_phase = (
            hype_entry.get("hype_phase")
            if isinstance(hype_entry, dict)
            else None
        ) or "early"

        # 1) Signal enter_long alors qu'un blocage fort existe
        if action == "enter_long" and (avoid_liquidity_pool or mm_detected or hype_block):
            anomalies.append(
                Anomaly(
                    id="ENTER_WITH_HARD_BLOCK",
                    severity="critical",
                    category="signal_vs_risk",
                    symbol=symbol_str,
                    description=(
                        "Signal enter_long alors qu'un blocage fort est actif "
                        "(liquidité / MM withdrawal / hype)."
                    ),
                    details={
                        "action": action,
                        "liquidity_risk_score": liq_score,
                        "avoid_liquidity_pool": avoid_liquidity_pool,
                        "mm_withdrawal_detected": mm_detected,
                        "mm_withdrawal_score": mm_score,
                        "hype_block_entry": hype_block,
                        "hype_score": hype_score,
                        "hype_phase": hype_phase,
                        "inputs": inputs,
                    },
                )
            )

        # 2) Signal enter_long alors que hype_score est très élevé (même sans block explicite)
        if action == "enter_long" and not hype_block and hype_score >= 85.0:
            anomalies.append(
                Anomaly(
                    id="ENTER_IN_EUPHORIC_HYPE",
                    severity="warning",
                    category="hype",
                    symbol=symbol_str,
                    description=(
                        "Signal enter_long sur un asset avec hype_score très élevé "
                        "(phase euphorique probable)."
                    ),
                    details={
                        "action": action,
                        "hype_score": hype_score,
                        "hype_phase": hype_phase,
                    },
                )
            )

        # 3) Signal enter_long avec liquidity_risk très élevé
        if action == "enter_long" and liq_score >= 80.0:
            anomalies.append(
                Anomaly(
                    id="ENTER_WITH_VERY_HIGH_LIQUIDITY_RISK",
                    severity="warning",
                    category="liquidity",
                    symbol=symbol_str,
                    description=(
                        "Signal enter_long avec un liquidity_risk_score >= 80. "
                        "Risque de pool/lack de liquidité."
                    ),
                    details={
                        "action": action,
                        "liquidity_risk_score": liq_score,
                        "avoid_liquidity_pool": avoid_liquidity_pool,
                    },
                )
            )

        # 4) Signal enter_long avec MM withdrawal fort
        if action == "enter_long" and (mm_detected or mm_score >= 75.0):
            anomalies.append(
                Anomaly(
                    id="ENTER_WITH_MM_WITHDRAWAL",
                    severity="warning",
                    category="mm_withdrawal",
                    symbol=symbol_str,
                    description=(
                        "Signal enter_long avec un signal fort de market maker withdrawal."
                    ),
                    details={
                        "action": action,
                        "mm_withdrawal_detected": mm_detected,
                        "mm_withdrawal_score": mm_score,
                    },
                )
            )

    return anomalies


# ---------------------------------------------------------------------------
# Global anomalies (portfolio / meta)
# ---------------------------------------------------------------------------

def _check_global_anomalies(
    signals: List[Dict[str, Any]],
    daily_feedback: Dict[str, Any],
    checklist: Dict[str, Any],
    emotional: Dict[str, Any],
) -> List[Anomaly]:
    anomalies: List[Anomaly] = []

    nb_signals = len(signals)
    nb_enter_long = sum(1 for s in signals if s.get("action") == "enter_long")
    nb_avoid = sum(1 for s in signals if s.get("action") == "avoid")

    meta_score_nsc = _safe_float(daily_feedback.get("meta_score_nsc"), 0.0)
    nb_open_positions = int(daily_feedback.get("nb_open_positions") or 0)
    realized_pnl_today = _safe_float(daily_feedback.get("realized_pnl_today"), 0.0)
    avg_momentum_meta = _safe_float(daily_feedback.get("avg_momentum_meta_score"), 0.0)

    checklist_score = _safe_float(checklist.get("score"), 100.0)
    checklist_all_ok = bool(checklist.get("all_ok", True))

    emotional_regime = emotional.get("regime") or "neutral"
    emotional_risk = emotional.get("risk_level") or "normal"
    losing_streak = int(emotional.get("losing_streak") or 0)
    overtrading_flag = bool(emotional.get("overtrading") or False)

    # A) Meta-score NSC faible mais beaucoup de signaux
    if meta_score_nsc < 40.0 and nb_enter_long >= 1:
        anomalies.append(
            Anomaly(
                id="MANY_SIGNALS_WITH_LOW_META_SCORE_NSC",
                severity="warning",
                category="governance",
                description=(
                    "Meta_score_nsc < 40 mais des signaux enter_long sont présents. "
                    "Incohérence potentielle entre le contexte global et l'agressivité du trading."
                ),
                details={
                    "meta_score_nsc": meta_score_nsc,
                    "nb_signals": nb_signals,
                    "nb_enter_long": nb_enter_long,
                    "nb_avoid": nb_avoid,
                    "avg_momentum_meta_score": avg_momentum_meta,
                },
            )
        )

    # B) Emotional regime en tilt / high_risk mais signaux agressifs
    if emotional_risk in ("high", "tilt") and nb_enter_long > 0:
        anomalies.append(
            Anomaly(
                id="AGGRESSIVE_TRADING_IN_EMOTIONAL_TILT",
                severity="critical",
                category="emotional",
                description=(
                    "Emotional_regime en mode risqué/tilt mais des signaux entrer en position sont actifs. "
                    "Risque élevé de décisions émotionnelles."
                ),
                details={
                    "emotional_regime": emotional_regime,
                    "emotional_risk_level": emotional_risk,
                    "losing_streak": losing_streak,
                    "overtrading": overtrading_flag,
                    "nb_enter_long": nb_enter_long,
                },
            )
        )

    # C) Checklist non respectée mais signaux présents
    if not checklist_all_ok and nb_enter_long > 0:
        anomalies.append(
            Anomaly(
                id="CHECKLIST_NOT_OK_WITH_NEW_ENTRIES",
                severity="critical",
                category="governance",
                description=(
                    "La checklist de gouvernance n'est pas entièrement respectée "
                    "mais de nouveaux signaux enter_long existent."
                ),
                details={
                    "checklist_score": checklist_score,
                    "checklist_all_ok": checklist_all_ok,
                    "nb_enter_long": nb_enter_long,
                },
            )
        )

    # D) Streak de pertes + positions encore ouvertes
    if losing_streak >= 3 and nb_open_positions == 0 and nb_enter_long > 0:
        anomalies.append(
            Anomaly(
                id="LOSING_STREAK_BUT_CONTINUING_TO_TRADE",
                severity="warning",
                category="risk",
                description=(
                    "Plusieurs pertes consécutives (losing_streak>=3) mais "
                    "de nouveaux signaux enter_long sont générés. "
                    "Une pause/revue pourrait être nécessaire."
                ),
                details={
                    "losing_streak": losing_streak,
                    "nb_open_positions": nb_open_positions,
                    "nb_enter_long": nb_enter_long,
                    "realized_pnl_today": realized_pnl_today,
                },
            )
        )

    return anomalies


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_anomalies() -> Dict[str, Any]:
    logger.info("[anomaly_engine_light] Calcul des anomalies...")

    signals = _load_signal_candidates()
    liquidity = _load_dict_file(LIQUIDITY_FILE)
    mm_withdrawal = _load_dict_file(MM_WITHDRAWAL_FILE)
    hype = _load_dict_file(HYPE_FILE)

    daily_feedback = _load_daily_feedback()
    checklist = _load_checklist()
    emotional = _load_emotional_regime()

    anomalies: List[Anomaly] = []

    # Per-asset
    anomalies.extend(
        _check_per_asset_anomalies(
            signals=signals,
            liquidity=liquidity,
            mm_withdrawal=mm_withdrawal,
            hype=hype,
        )
    )

    # Global
    anomalies.extend(
        _check_global_anomalies(
            signals=signals,
            daily_feedback=daily_feedback,
            checklist=checklist,
            emotional=emotional,
        )
    )

    nb_critical = sum(1 for a in anomalies if a.severity == "critical")
    nb_warning = sum(1 for a in anomalies if a.severity == "warning")

    overview = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "nb_anomalies": len(anomalies),
            "nb_critical": nb_critical,
            "nb_warning": nb_warning,
        },
        "anomalies": [a.to_dict() for a in anomalies],
    }

    logger.info(
        "[anomaly_engine_light] Anomalies détectées: total=%d, critical=%d, warning=%d",
        len(anomalies),
        nb_critical,
        nb_warning,
    )

    return overview


def save_anomalies(overview: Dict[str, Any]) -> None:
    _save_json(OUTPUT_FILE, overview)
    logger.info("[anomaly_engine_light] Résultat sauvegardé dans %s", OUTPUT_FILE)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    overview = compute_anomalies()
    save_anomalies(overview)


if __name__ == "__main__":
    main()
