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
class FractalEnergyMetrics:
    """
    Métriques de Fractal Energy / structure de mouvement.

    JSON attendu (souple) dans data/analysis/fractal_energy.json par ex. :

    {
      "fractal_energy": 0.72,        # 0–1 (0 = très compressé, 1 = très "chargé")
      "trend_bias_up": 0.65,         # 0–1
      "trend_bias_down": 0.10,       # 0–1
      "compression_score": 0.20,     # 0–1
      "expansion_score": 0.70,       # 0–1
      "multi_tf_alignment": 0.65     # 0–1 (cohérence des TF)
    }
    """

    fractal_energy: Optional[float]
    trend_bias_up: Optional[float]
    trend_bias_down: Optional[float]
    compression_score: Optional[float]
    expansion_score: Optional[float]
    multi_tf_alignment: Optional[float]


def _get_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def load_fractal_energy_metrics(raw: Any) -> FractalEnergyMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return FractalEnergyMetrics(
        fractal_energy=_get_float(raw.get("fractal_energy")),
        trend_bias_up=_get_float(raw.get("trend_bias_up")),
        trend_bias_down=_get_float(raw.get("trend_bias_down")),
        compression_score=_get_float(raw.get("compression_score")),
        expansion_score=_get_float(raw.get("expansion_score")),
        multi_tf_alignment=_get_float(raw.get("multi_tf_alignment")),
    )


# ---------------------------------------------------------------------------
# Logic Fractal Energy Engine
# ---------------------------------------------------------------------------

def infer_fractal_regime_and_score(
    metrics: FractalEnergyMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime "Fractal Energy" + flag global + score.

    Intuition :
    - FE très basse  → marché comprimé / range → piège à breakout (caution)
    - FE moyenne    → état "normal" / équilibré
    - FE élevée     → marché "chargé" en énergie, prêt pour des mouvements forts
      • si bias up + alignement multi-TF → trending_up (supportive)
      • si bias down + alignement + expansion → trending_down (caution / risk_off)
    """

    reasons: List[str] = []

    fe = metrics.fractal_energy
    up = metrics.trend_bias_up
    down = metrics.trend_bias_down
    comp = metrics.compression_score
    exp = metrics.expansion_score
    align = metrics.multi_tf_alignment

    values = [v for v in (fe, up, down, comp, exp, align) if v is not None]
    if not values:
        reasons.append("Aucune donnée de Fractal Energy exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    # Seuils raisonnables (0–1)
    FE_LOW = 0.35
    FE_HIGH = 0.65
    ALIGN_GOOD = 0.6
    BIAS_STRONG = 0.55
    COMP_HIGH = 0.6
    EXP_HIGH = 0.6

    regime = "unknown"
    global_flag = "caution"
    score = 50.0

    # 1) Cas "compressed" : faible FE + compression forte
    if fe is not None and fe <= FE_LOW and (comp is not None and comp >= COMP_HIGH):
        regime = "compressed"
        global_flag = "caution"
        score = 45.0
        msg = (
            "RÉGIME FRACTAL COMPRESSED : énergie basse, marché en range / congestion. "
            f"fractal_energy={fe:.2f}, compression_score={comp:.2f}"
        )
        if align is not None:
            msg += f", multi_tf_alignment={align:.2f}"
        reasons.append(msg)

    # 2) Cas "trending_up" : FE élevée + bias up + alignement
    elif (
        fe is not None and fe >= FE_HIGH
        and up is not None and up >= BIAS_STRONG
        and (align is None or align >= ALIGN_GOOD)
    ):
        regime = "trending_up"
        global_flag = "supportive"
        score = 65.0
        msg = (
            "RÉGIME FRACTAL TRENDING_UP : forte énergie + biais haussier. "
            f"fractal_energy={fe:.2f}, trend_bias_up={up:.2f}"
        )
        if exp is not None:
            msg += f", expansion_score={exp:.2f}"
        if align is not None:
            msg += f", multi_tf_alignment={align:.2f}"
        reasons.append(msg)

    # 3) Cas "trending_down" : FE élevée + bias down + expansion + alignement
    elif (
        fe is not None and fe >= FE_HIGH
        and down is not None and down >= BIAS_STRONG
        and (exp is not None and exp >= EXP_HIGH)
    ):
        regime = "trending_down"
        global_flag = "risk_off"
        score = 40.0
        msg = (
            "RÉGIME FRACTAL TRENDING_DOWN : forte énergie baissière, risque de dérapage. "
            f"fractal_energy={fe:.2f}, trend_bias_down={down:.2f}, expansion_score={exp:.2f}"
        )
        if align is not None:
            msg += f", multi_tf_alignment={align:.2f}"
        reasons.append(msg)

    # 4) Cas "balanced" : FE moyenne → état neutre/supportive
    elif fe is not None and FE_LOW < fe < FE_HIGH:
        regime = "balanced"
        global_flag = "neutral"
        score = 55.0
        msg = (
            "RÉGIME FRACTAL BALANCED : énergie moyenne, structure de marché normale. "
            f"fractal_energy={fe:.2f}"
        )
        if comp is not None:
            msg += f", compression_score={comp:.2f}"
        if exp is not None:
            msg += f", expansion_score={exp:.2f}"
        reasons.append(msg)

    # 5) Fallback : FE connue mais pas de cas bien tranché
    else:
        regime = "mixed"
        global_flag = "caution"
        score = 50.0
        msg = "RÉGIME FRACTAL MIXED : signaux contradictoires."
        if fe is not None:
            msg += f" fractal_energy={fe:.2f}."
        if up is not None:
            msg += f" trend_bias_up={up:.2f}."
        if down is not None:
            msg += f" trend_bias_down={down:.2f}."
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


def build_fractal_energy_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état Fractal Energy à partir de :

    data/analysis/fractal_energy.json
    """
    src_file = data_dir / "analysis" / "fractal_energy.json"
    raw = load_json_file(src_file, default={})

    metrics = load_fractal_energy_metrics(raw)
    regime, global_flag, score, reasons = infer_fractal_regime_and_score(metrics)
    severity = severity_from_flag(global_flag)

    # Timestamp UTC
    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": {
            "fractal_energy": metrics.fractal_energy,
            "trend_bias_up": metrics.trend_bias_up,
            "trend_bias_down": metrics.trend_bias_down,
            "compression_score": metrics.compression_score,
            "expansion_score": metrics.expansion_score,
            "multi_tf_alignment": metrics.multi_tf_alignment,
        },
        "reasons": reasons,
    }

    logger.info(
        "[fractal_energy_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f, "
        "fe=%s, up=%s, down=%s, comp=%s, exp=%s, align=%s",
        env,
        regime,
        global_flag,
        score,
        f"{metrics.fractal_energy:.2f}" if metrics.fractal_energy is not None else "None",
        f"{metrics.trend_bias_up:.2f}" if metrics.trend_bias_up is not None else "None",
        f"{metrics.trend_bias_down:.2f}" if metrics.trend_bias_down is not None else "None",
        f"{metrics.compression_score:.2f}" if metrics.compression_score is not None else "None",
        f"{metrics.expansion_score:.2f}" if metrics.expansion_score is not None else "None",
        f"{metrics.multi_tf_alignment:.2f}" if metrics.multi_tf_alignment is not None else "None",
    )

    return state, severity


def main() -> None:
    data_dir = get_data_dir()
    env = get_env()

    logger.info(
        "[fractal_energy_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_fractal_energy_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "fractal_energy_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[fractal_energy_engine_pro] fractal_energy_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication event
    publish_event(
        event_type="fractal.energy.state",
        source="fractal_energy_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[fractal_energy_engine_pro] Event fractal.energy.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
