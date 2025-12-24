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
class MarketMemoryMetrics:
    """
    Métriques de "Market Memory" / persistance de régime.

    JSON attendu dans data/analysis/market_memory.json (souple) :

    {
      "memory_score": 0.72,            # 0–1 (0 = amnésique, 1 = très persistant)
      "trend_persistence": 0.65,       # 0–1 (persistance directionnelle des rendements)
      "mean_reversion_score": 0.20,    # 0–1
      "breakout_memory_score": 0.55,   # 0–1 (persistance après breakouts)
      "shock_memory_score": 0.30,      # 0–1 (impact résiduel des gros chocs)
      "regime_stability": 0.60         # 0–1 (fréquence de switching de régime)
    }
    """

    memory_score: Optional[float]
    trend_persistence: Optional[float]
    mean_reversion_score: Optional[float]
    breakout_memory_score: Optional[float]
    shock_memory_score: Optional[float]
    regime_stability: Optional[float]


def _get_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def load_market_memory_metrics(raw: Any) -> MarketMemoryMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return MarketMemoryMetrics(
        memory_score=_get_float(raw.get("memory_score")),
        trend_persistence=_get_float(raw.get("trend_persistence")),
        mean_reversion_score=_get_float(raw.get("mean_reversion_score")),
        breakout_memory_score=_get_float(raw.get("breakout_memory_score")),
        shock_memory_score=_get_float(raw.get("shock_memory_score")),
        regime_stability=_get_float(raw.get("regime_stability")),
    )


# ---------------------------------------------------------------------------
# Logic Market Memory Engine
# ---------------------------------------------------------------------------

def infer_market_memory_regime_and_score(
    metrics: MarketMemoryMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de "Market Memory" + flag global + score.

    Intuition :
    - memory_score élevé + trend_persistence élevée :
        → marché qui "se souvient" de la tendance → pro-trend
    - memory_score élevé + mean_reversion_score élevé :
        → patterns de retour à la moyenne → éviter poursuite naïve
    - memory_score faible + regime_stability faible :
        → bruit, régimes qui changent → prudence
    """

    reasons: List[str] = []

    m = metrics.memory_score
    tp = metrics.trend_persistence
    mr = metrics.mean_reversion_score
    bo = metrics.breakout_memory_score
    sh = metrics.shock_memory_score
    rs = metrics.regime_stability

    values = [v for v in (m, tp, mr, bo, sh, rs) if v is not None]
    if not values:
        reasons.append("Aucune donnée de Market Memory exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    # Seuils (0–1)
    LOW = 0.35
    HIGH = 0.65
    MID = 0.5

    regime = "unknown"
    global_flag = "caution"
    score = 50.0

    # 1) Regime très pro-trend
    if (
        m is not None and m >= HIGH
        and tp is not None and tp >= HIGH
        and (mr is None or mr <= MID)
    ):
        regime = "trend_memory"
        global_flag = "supportive"
        score = 65.0
        msg = (
            "MARKET MEMORY TREND : forte persistance directionnelle. "
            f"memory_score={m:.2f}, trend_persistence={tp:.2f}"
        )
        if rs is not None:
            msg += f", regime_stability={rs:.2f}"
        if bo is not None:
            msg += f", breakout_memory_score={bo:.2f}"
        reasons.append(msg)

    # 2) Regime mean-reverting marqué
    elif (
        m is not None and m >= MID
        and mr is not None and mr >= HIGH
    ):
        regime = "mean_reversion_memory"
        global_flag = "caution"
        score = 45.0
        msg = (
            "MARKET MEMORY MEAN-REVERTING : patterns de retour à la moyenne dominants. "
            f"memory_score={m:.2f}, mean_reversion_score={mr:.2f}"
        )
        if tp is not None:
            msg += f", trend_persistence={tp:.2f}"
        reasons.append(msg)

    # 3) Regime instable / bruit
    elif (
        (m is not None and m <= LOW)
        or (rs is not None and rs <= LOW)
    ):
        regime = "memory_weak"
        global_flag = "caution"
        score = 48.0
        msg = (
            "MARKET MEMORY WEAK : faible persistance, régimes instables ou bruités."
        )
        if m is not None:
            msg += f" memory_score={m:.2f}."
        if rs is not None:
            msg += f" regime_stability={rs:.2f}."
        reasons.append(msg)

    # 4) Regime avec mémoire de chocs (risk_off soft)
    elif (
        sh is not None and sh >= HIGH
    ):
        regime = "shock_memory"
        global_flag = "caution"
        score = 45.0
        msg = (
            "MARKET MEMORY SHOCK : forte mémoire des chocs récents, prudence sur les tailles."
            f" shock_memory_score={sh:.2f}"
        )
        if m is not None:
            msg += f", memory_score={m:.2f}"
        reasons.append(msg)

    # 5) Regime équilibré
    else:
        regime = "balanced"
        global_flag = "neutral"
        score = 55.0
        msg = "MARKET MEMORY BALANCED : aucune dominante forte, régime équilibré."
        if m is not None:
            msg += f" memory_score={m:.2f}."
        if tp is not None:
            msg += f" trend_persistence={tp:.2f}."
        if mr is not None:
            msg += f" mean_reversion_score={mr:.2f}."
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


def build_market_memory_state(data_dir: Path, env: str) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état Market Memory à partir de :

    data/analysis/market_memory.json
    """
    src_file = data_dir / "analysis" / "market_memory.json"
    raw = load_json_file(src_file, default={})

    metrics = load_market_memory_metrics(raw)
    regime, global_flag, score, reasons = infer_market_memory_regime_and_score(metrics)
    severity = severity_from_flag(global_flag)

    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": {
            "memory_score": metrics.memory_score,
            "trend_persistence": metrics.trend_persistence,
            "mean_reversion_score": metrics.mean_reversion_score,
            "breakout_memory_score": metrics.breakout_memory_score,
            "shock_memory_score": metrics.shock_memory_score,
            "regime_stability": metrics.regime_stability,
        },
        "reasons": reasons,
    }

    logger.info(
        "[market_memory_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f, "
        "memory=%s, trend_persistence=%s, mean_reversion=%s, breakout=%s, shock=%s, regime_stability=%s",
        env,
        regime,
        global_flag,
        score,
        f"{metrics.memory_score:.2f}" if metrics.memory_score is not None else "None",
        f"{metrics.trend_persistence:.2f}" if metrics.trend_persistence is not None else "None",
        f"{metrics.mean_reversion_score:.2f}" if metrics.mean_reversion_score is not None else "None",
        f"{metrics.breakout_memory_score:.2f}" if metrics.breakout_memory_score is not None else "None",
        f"{metrics.shock_memory_score:.2f}" if metrics.shock_memory_score is not None else "None",
        f"{metrics.regime_stability:.2f}" if metrics.regime_stability is not None else "None",
    )

    return state, severity


def main() -> None:
    data_dir = get_data_dir()
    env = get_env()

    logger.info(
        "[market_memory_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_market_memory_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "market_memory_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[market_memory_engine_pro] market_memory_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication event
    publish_event(
        event_type="market.memory.state",
        source="market_memory_engine_pro",
        severity=severity,
        payload=state,
    )
    logger.info(
        "[market_memory_engine_pro] Event market.memory.state publié "
        "(severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
