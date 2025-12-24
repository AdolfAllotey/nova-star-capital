from __future__ import annotations

import os
import math
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers env / data_dir
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """
    Renvoie le dossier data de NSC.

    - Si NSC_DATA_DIR est défini : on l'utilise.
    - Sinon : 'data' relatif au cwd (/opt/nsc/app).
    """
    base = os.getenv("NSC_DATA_DIR", "data")
    return Path(base).resolve()


def get_env() -> str:
    """Renvoie l'environnement courant ('PREPROD' par défaut)."""
    return os.getenv("NSC_ENV", "PREPROD")


# ---------------------------------------------------------------------------
# Dataclass & helpers
# ---------------------------------------------------------------------------

@dataclass
class RegimeTransitionMetrics:
    """
    Métriques de risque de transition de régime.

    JSON attendu (souple) dans data/analysis/regime_transition_signals.json :

    {
      "transition_probability": 0.35,     # 0–1
      "macro_regime_shift": 0.4,          # 0–1
      "micro_regime_shift": 0.6,          # 0–1 (orderflow / microstructure)
      "duration_in_state_days": 25,       # nb jours dans le régime actuel
      "vol_state_score": 0.5,             # 0–1 (volatility_state_machine)
      "liquidity_state_score": 0.4        # 0–1 (liquidity engines)
    }
    """

    transition_probability: Optional[float]
    macro_regime_shift: Optional[float]
    micro_regime_shift: Optional[float]
    duration_in_state_days: Optional[int]
    vol_state_score: Optional[float]
    liquidity_state_score: Optional[float]


def _get_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _get_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_regime_transition_metrics(raw: Any) -> RegimeTransitionMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return RegimeTransitionMetrics(
        transition_probability=_get_float(raw.get("transition_probability")),
        macro_regime_shift=_get_float(raw.get("macro_regime_shift")),
        micro_regime_shift=_get_float(raw.get("micro_regime_shift")),
        duration_in_state_days=_get_int(raw.get("duration_in_state_days")),
        vol_state_score=_get_float(raw.get("vol_state_score")),
        liquidity_state_score=_get_float(raw.get("liquidity_state_score")),
    )


# ---------------------------------------------------------------------------
# Logic Regime Transition
# ---------------------------------------------------------------------------

def infer_regime_transition_regime_and_score(
    m: RegimeTransitionMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de transition + flag global + score NSC.

    Idée :
    - transition_probability & shifts élevés → "transition_active" / risk_off
    - signaux modérés → "transition_watch" / caution
    - pas de signaux → "stable" / supportive
    """

    reasons: List[str] = []

    values = [
        v
        for v in (
            m.transition_probability,
            m.macro_regime_shift,
            m.micro_regime_shift,
            m.vol_state_score,
            m.liquidity_state_score,
        )
        if v is not None
    ]
    if not values:
        reasons.append("Aucune donnée de transition de régime exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    # Seuils
    HIGH_P = 0.65
    MID_P = 0.35
    HIGH_SHIFT = 0.65
    MID_SHIFT = 0.45
    LONG_STATE = 60  # jours dans le même régime

    regime = "unknown"
    global_flag = "caution"
    score = 50.0

    tp = m.transition_probability
    macro = m.macro_regime_shift
    micro = m.micro_regime_shift
    vol_s = m.vol_state_score
    liq_s = m.liquidity_state_score
    dur = m.duration_in_state_days

    # 1) Transition active / risque élevé
    if (
        (tp is not None and tp >= HIGH_P)
        or (
            macro is not None and macro >= HIGH_SHIFT
            and micro is not None and micro >= HIGH_SHIFT
        )
        or (
            vol_s is not None and vol_s >= HIGH_SHIFT
            and liq_s is not None and liq_s >= HIGH_SHIFT
        )
    ):
        regime = "transition_active"
        global_flag = "risk_off"
        score = 40.0

        msg = (
            "REGIME TRANSITION – ACTIVE : probabilité de transition ou "
            "intensité des shifts très élevée, mode défensif recommandé."
        )
        parts = []
        if tp is not None:
            parts.append(f"transition_probability={tp:.2f}")
        if macro is not None:
            parts.append(f"macro_regime_shift={macro:.2f}")
        if micro is not None:
            parts.append(f"micro_regime_shift={micro:.2f}")
        if vol_s is not None:
            parts.append(f"vol_state_score={vol_s:.2f}")
        if liq_s is not None:
            parts.append(f"liquidity_state_score={liq_s:.2f}")
        if dur is not None:
            parts.append(f"duration_in_state_days={dur}")
        if parts:
            msg += " " + ", ".join(parts)
        reasons.append(msg)

    # 2) Transition sous surveillance / risque modéré
    elif (
        (tp is not None and tp >= MID_P)
        or (macro is not None and macro >= MID_SHIFT)
        or (micro is not None and micro >= MID_SHIFT)
        or (
            dur is not None and dur >= LONG_STATE
        )  # long séjour dans le même régime + signaux moyens = fatigue du régime
    ):
        regime = "transition_watch"
        global_flag = "caution"
        score = 47.0

        msg = (
            "REGIME TRANSITION – WATCH : signaux de changement de régime présents, "
            "mais sans rupture confirmée."
        )
        parts = []
        if tp is not None:
            parts.append(f"transition_probability={tp:.2f}")
        if macro is not None:
            parts.append(f"macro_regime_shift={macro:.2f}")
        if micro is not None:
            parts.append(f"micro_regime_shift={micro:.2f}")
        if dur is not None:
            parts.append(f"duration_in_state_days={dur}")
        if parts:
            msg += " " + ", ".join(parts)
        reasons.append(msg)

    # 3) Régime stable / pas de transition visible
    else:
        regime = "stable"
        global_flag = "supportive"
        score = 60.0

        msg = (
            "REGIME TRANSITION – STABLE : peu de signaux de changement de régime, "
            "structure globale cohérente."
        )
        parts = []
        if tp is not None:
            parts.append(f"transition_probability={tp:.2f}")
        if dur is not None:
            parts.append(f"duration_in_state_days={dur}")
        if parts:
            msg += " " + ", ".join(parts)
        reasons.append(msg)

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    if global_flag in ("supportive", "neutral"):
        return "info"
    if global_flag == "caution":
        return "warning"
    if global_flag == "risk_off":
        return "critical"
    return "info"


def build_regime_transition_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de Regime Transition à partir de :

    data/analysis/regime_transition_signals.json
    """
    src_file = data_dir / "analysis" / "regime_transition_signals.json"
    raw = load_json_file(src_file, default={})

    metrics = load_regime_transition_metrics(raw)
    regime, global_flag, score, reasons = infer_regime_transition_regime_and_score(metrics)

    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": {
            "transition_probability": metrics.transition_probability,
            "macro_regime_shift": metrics.macro_regime_shift,
            "micro_regime_shift": metrics.micro_regime_shift,
            "duration_in_state_days": metrics.duration_in_state_days,
            "vol_state_score": metrics.vol_state_score,
            "liquidity_state_score": metrics.liquidity_state_score,
        },
        "reasons": reasons,
    }

    severity = severity_from_flag(global_flag)
    return state, severity


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    data_dir = get_data_dir()
    env = get_env()
    logger.info(
        "[regime_transition_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_regime_transition_state(data_dir=data_dir, env=env)

    logger.info(
        "[regime_transition_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f",
        env,
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    out_file = data_dir / "analysis" / "regime_transition_engine_pro.json"
    save_json_file(out_file, state)
    logger.info(
        "[regime_transition_engine_pro] regime_transition_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    try:
        publish_event(
            "regime.transition.state",
            "regime_transition_engine_pro",
            severity=severity,
            payload=state,
        )
        logger.info(
            "[regime_transition_engine_pro] Event regime.transition.state publié (severity=%s, score=%.2f)",
            severity,
            state.get("score"),
        )
    except Exception as exc:  # pragma: no cover
        logger.error(
            "[regime_transition_engine_pro] Impossible de publier l'event regime.transition.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
