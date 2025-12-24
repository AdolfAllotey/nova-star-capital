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
class StructuralBreakMetrics:
    """
    Metrices de "Structural Breaks" – changements de régime marqués.

    Structure JSON attendue (flexible) dans data/analysis/structural_breaks.json :

    {
      "nb_breaks_90d": 3,          # nombre de breaks significatifs sur 90 jours
      "last_break_days_ago": 5,    # nb de jours depuis le dernier break
      "avg_magnitude": 0.12,       # magnitude moyenne (0–1) des breaks
      "vol_shift": 0.30,           # shift moyen de volatilité
      "corr_shift": 0.25,          # shift moyen des corrélations
      "regime_shift_score": 0.7    # synthèse 0–1 de "changement de régime"
    }
    """

    nb_breaks_90d: Optional[float]
    last_break_days_ago: Optional[float]
    avg_magnitude: Optional[float]
    vol_shift: Optional[float]
    corr_shift: Optional[float]
    regime_shift_score: Optional[float]


def _get_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def load_structural_break_metrics(raw: Any) -> StructuralBreakMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return StructuralBreakMetrics(
        nb_breaks_90d=_get_float(raw.get("nb_breaks_90d")),
        last_break_days_ago=_get_float(raw.get("last_break_days_ago")),
        avg_magnitude=_get_float(raw.get("avg_magnitude")),
        vol_shift=_get_float(raw.get("vol_shift")),
        corr_shift=_get_float(raw.get("corr_shift")),
        regime_shift_score=_get_float(raw.get("regime_shift_score")),
    )


# ---------------------------------------------------------------------------
# Logic Structural Break Engine
# ---------------------------------------------------------------------------

def infer_structural_break_regime_and_score(
    metrics: StructuralBreakMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de structural breaks + flag + score.

    Idée :
    - Regime "unstable" : gros breaks récents, régime shift élevé → risk_off
    - Regime "transition" : signaux de changement en cours → caution
    - Regime "stable" : peu de breaks, magnitudes faibles → supportive
    """

    reasons: List[str] = []

    nb = metrics.nb_breaks_90d
    last = metrics.last_break_days_ago
    mag = metrics.avg_magnitude
    vol = metrics.vol_shift
    corr = metrics.corr_shift
    rs = metrics.regime_shift_score

    values = [v for v in (nb, last, mag, vol, corr, rs) if v is not None]
    if not values:
        reasons.append("Aucune donnée de structural breaks exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    # Interprétation (0–1)
    high_regime_shift = rs is not None and rs >= 0.7
    medium_regime_shift = rs is not None and 0.5 <= rs < 0.7

    many_breaks = nb is not None and nb >= 4
    some_breaks = nb is not None and 1 <= nb < 4

    recent_break = last is not None and last <= 10
    very_recent_break = last is not None and last <= 3

    strong_mag = mag is not None and mag >= 0.10
    medium_mag = mag is not None and 0.05 <= mag < 0.10

    strong_vol_shift = vol is not None and vol >= 0.25
    strong_corr_shift = corr is not None and corr >= 0.25

    # 1) Cas "unstable" / risk_off : gros changement de régime récent
    if (
        high_regime_shift
        or (many_breaks and (strong_mag or strong_vol_shift or strong_corr_shift))
        or (very_recent_break and strong_mag)
    ):
        regime = "unstable"
        global_flag = "risk_off"
        score = 35.0

        msg = "RÉGIME STRUCTURAL UNSTABLE : "
        details = []
        if rs is not None:
            details.append(f"regime_shift_score={rs:.2f}")
        if nb is not None:
            details.append(f"nb_breaks_90d={nb:.0f}")
        if last is not None:
            details.append(f"last_break_days_ago={last:.1f}")
        if mag is not None:
            details.append(f"avg_magnitude={mag:.2f}")
        if vol is not None:
            details.append(f"vol_shift={vol:.2f}")
        if corr is not None:
            details.append(f"corr_shift={corr:.2f}")
        msg += ", ".join(details)
        reasons.append(msg)

    # 2) Cas "transition" : signaux de changements significatifs mais moins extrêmes
    elif medium_regime_shift or (some_breaks and (medium_mag or strong_vol_shift or strong_corr_shift)):
        regime = "transition"
        global_flag = "caution"
        score = 45.0

        msg = "RÉGIME STRUCTURAL EN TRANSITION : "
        details = []
        if rs is not None:
            details.append(f"regime_shift_score={rs:.2f}")
        if nb is not None:
            details.append(f"nb_breaks_90d={nb:.0f}")
        if last is not None:
            details.append(f"last_break_days_ago={last:.1f}")
        if mag is not None:
            details.append(f"avg_magnitude={mag:.2f}")
        if vol is not None:
            details.append(f"vol_shift={vol:.2f}")
        if corr is not None:
            details.append(f"corr_shift={corr:.2f}")
        msg += ", ".join(details)
        reasons.append(msg)

    # 3) Cas "stable" : peu de breaks, effets faibles
    else:
        regime = "stable"
        global_flag = "supportive"
        score = 60.0

        msg = "RÉGIME STRUCTURAL STABLE : "
        msg += "peu de breaks significatifs ou magnitudes faibles."
        if nb is not None:
            msg += f" nb_breaks_90d={nb:.0f}."
        if mag is not None:
            msg += f" avg_magnitude={mag:.2f}."
        reasons.append(msg)

    return regime, global_flag, score, reasons


def severity_from_flag(global_flag: str) -> str:
    if global_flag == "supportive":
        return "info"
    if global_flag == "neutral":
        return "info"
    if global_flag == "caution":
        return "warning"
    if global_flag == "risk_off":
        return "critical"
    return "info"


def build_structural_break_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de "Structural Breaks" à partir de :

    data/analysis/structural_breaks.json
    """
    src_file = data_dir / "analysis" / "structural_breaks.json"
    raw = load_json_file(src_file, default={})

    metrics = load_structural_break_metrics(raw)
    regime, global_flag, score, reasons = infer_structural_break_regime_and_score(metrics)
    severity = severity_from_flag(global_flag)

    # Timestamp UTC (comme les autres moteurs déjà en prod)
    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": {
            "nb_breaks_90d": metrics.nb_breaks_90d,
            "last_break_days_ago": metrics.last_break_days_ago,
            "avg_magnitude": metrics.avg_magnitude,
            "vol_shift": metrics.vol_shift,
            "corr_shift": metrics.corr_shift,
            "regime_shift_score": metrics.regime_shift_score,
        },
        "reasons": reasons,
    }

    logger.info(
        "[structural_break_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f, "
        "nb_breaks_90d=%s, last_break_days_ago=%s, avg_magnitude=%s, "
        "vol_shift=%s, corr_shift=%s, regime_shift_score=%s",
        env,
        regime,
        global_flag,
        score,
        f"{metrics.nb_breaks_90d:.0f}" if metrics.nb_breaks_90d is not None else "None",
        f"{metrics.last_break_days_ago:.1f}" if metrics.last_break_days_ago is not None else "None",
        f"{metrics.avg_magnitude:.2f}" if metrics.avg_magnitude is not None else "None",
        f"{metrics.vol_shift:.2f}" if metrics.vol_shift is not None else "None",
        f"{metrics.corr_shift:.2f}" if metrics.corr_shift is not None else "None",
        f"{metrics.regime_shift_score:.2f}" if metrics.regime_shift_score is not None else "None",
    )

    return state, severity


def main() -> None:
    data_dir = get_data_dir()
    env = get_env()

    logger.info(
        "[structural_break_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_structural_break_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "structural_break_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[structural_break_engine_pro] structural_break_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication event
    publish_event(
        event_type="structural.break.state",
        source="structural_break_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[structural_break_engine_pro] Event structural.break.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
