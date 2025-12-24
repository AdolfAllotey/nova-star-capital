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
class MarketStrengthMetrics:
    """
    Métriques de Market Strength agrégées cross-asset.

    Fichier attendu : data/analysis/market_strength.json

    Format souple, par exemple :

    {
      "breadth_score": 0.7,              # 0–1, pourcentage / qualité de titres en hausse
      "leadership_score": 0.65,          # 0–1, qualité des leaders (large caps, sectors clés)
      "high_low_score": 0.6,             # 0–1, balance new highs / new lows
      "momentum_breadth_score": 0.7,     # 0–1, % d'actifs avec momentum > seuil
      "divergence_score": 0.3,           # 0–1, 0 = pas de divergence, 1 = divergences fortes
      "adv_decline_ratio": 1.8,          # >1 = plus de hausses, <1 = plus de baisses
      "pct_above_ma": 0.62,              # 0–1, % d'actifs au-dessus de leur MA clé
      "nb_new_highs": 120,
      "nb_new_lows": 40,
      "nb_assets": 450
    }
    """

    breadth_score: Optional[float]
    leadership_score: Optional[float]
    high_low_score: Optional[float]
    momentum_breadth_score: Optional[float]
    divergence_score: Optional[float]
    adv_decline_ratio: Optional[float]
    pct_above_ma: Optional[float]
    nb_new_highs: Optional[int]
    nb_new_lows: Optional[int]
    nb_assets: Optional[int]


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


def load_market_strength_metrics(raw: Any) -> MarketStrengthMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return MarketStrengthMetrics(
        breadth_score=_get_float(raw.get("breadth_score")),
        leadership_score=_get_float(raw.get("leadership_score")),
        high_low_score=_get_float(raw.get("high_low_score")),
        momentum_breadth_score=_get_float(raw.get("momentum_breadth_score")),
        divergence_score=_get_float(raw.get("divergence_score")),
        adv_decline_ratio=_get_float(raw.get("adv_decline_ratio")),
        pct_above_ma=_get_float(raw.get("pct_above_ma")),
        nb_new_highs=_get_int(raw.get("nb_new_highs")),
        nb_new_lows=_get_int(raw.get("nb_new_lows")),
        nb_assets=_get_int(raw.get("nb_assets")),
    )


# ---------------------------------------------------------------------------
# Logique Market Strength
# ---------------------------------------------------------------------------

def infer_market_strength_regime_and_score(
    m: MarketStrengthMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de Market Strength + flag global + score NSC.

    Intuition :

    - Large majorité d'actifs en hausse, leaders solides, beaucoup de new highs
      → "strong_uptrend" → global_flag = "supportive" → score > 60.
    - Large majorité d'actifs en baisse, leaders en panne, beaucoup de new lows
      → "strong_downtrend" → global_flag = "risk_off" → score < 45.
    - Breadth mitigée / divergences → "mixed" → global_flag = "caution".
    - Pas de données → "unknown" / neutre.
    """

    reasons: List[str] = []

    core_values = [
        v
        for v in (
            m.breadth_score,
            m.leadership_score,
            m.high_low_score,
            m.momentum_breadth_score,
            m.pct_above_ma,
        )
        if v is not None
    ]
    if not core_values:
        reasons.append("Aucune donnée de Market Strength exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    breadth = m.breadth_score
    leaders = m.leadership_score
    high_low = m.high_low_score
    mom_breadth = m.momentum_breadth_score
    divergence = m.divergence_score
    adv_dec = m.adv_decline_ratio
    pct_ma = m.pct_above_ma
    nh = m.nb_new_highs
    nl = m.nb_new_lows
    nb_assets = m.nb_assets

    HIGH = 0.65
    VERY_HIGH = 0.75
    LOW = 0.35
    MID = 0.5
    DIVERGENCE_HIGH = 0.65

    regime = "unknown"
    global_flag = "caution"
    score = 50.0

    # ------------------------------------------------------------------
    # 1) Trend fort haussier / Market Strength élevé (context risk_on)
    # ------------------------------------------------------------------
    strong_up = False
    expl_up: List[str] = []

    up_conditions = 0
    if breadth is not None and breadth >= HIGH:
        up_conditions += 1
        expl_up.append(f"breadth_score={breadth:.2f}")
    if leaders is not None and leaders >= HIGH:
        up_conditions += 1
        expl_up.append(f"leadership_score={leaders:.2f}")
    if high_low is not None and high_low >= HIGH:
        up_conditions += 1
        expl_up.append(f"high_low_score={high_low:.2f}")
    if mom_breadth is not None and mom_breadth >= HIGH:
        up_conditions += 1
        expl_up.append(f"momentum_breadth_score={mom_breadth:.2f}")
    if pct_ma is not None and pct_ma >= HIGH:
        up_conditions += 1
        expl_up.append(f"pct_above_ma={pct_ma:.2f}")
    if adv_dec is not None and adv_dec >= 1.5:
        up_conditions += 1
        expl_up.append(f"adv_decline_ratio={adv_dec:.2f}")

    if up_conditions >= 3:
        strong_up = True

    if strong_up:
        regime = "strong_uptrend"
        global_flag = "supportive"

        # Score base
        avg_core = sum(core_values) / len(core_values)
        score = min(80.0, 60.0 + (avg_core - MID) * 40.0)

        msg = (
            "MARKET STRENGTH – STRONG UPTREND : largeur de marché solide, "
            "leaders actifs et dynamique positive sur un grand nombre d'actifs."
        )
        if nh is not None and nl is not None:
            msg += f" new_highs={nh}, new_lows={nl}."
        if nb_assets is not None:
            expl_up.append(f"nb_assets={nb_assets}")
        if expl_up:
            msg += " " + ", ".join(expl_up)

        # Si divergences fortes, on nuance.
        if divergence is not None and divergence >= DIVERGENCE_HIGH:
            msg += (
                f" Attention : divergences marquées détectées (divergence_score={divergence:.2f}) – "
                "le mouvement haussier pourrait être fragile."
            )
            # On réduit légèrement le score si divergence forte
            score = max(55.0, score - 5.0)

        reasons.append(msg)
        return regime, global_flag, score, reasons

    # ------------------------------------------------------------------
    # 2) Trend fort baissier / Market Strength très faible (risk_off)
    # ------------------------------------------------------------------
    strong_down = False
    expl_down: List[str] = []

    down_conditions = 0
    if breadth is not None and breadth <= LOW:
        down_conditions += 1
        expl_down.append(f"breadth_score={breadth:.2f}")
    if leaders is not None and leaders <= LOW:
        down_conditions += 1
        expl_down.append(f"leadership_score={leaders:.2f}")
    if high_low is not None and high_low <= LOW:
        down_conditions += 1
        expl_down.append(f"high_low_score={high_low:.2f}")
    if mom_breadth is not None and mom_breadth <= LOW:
        down_conditions += 1
        expl_down.append(f"momentum_breadth_score={mom_breadth:.2f}")
    if pct_ma is not None and pct_ma <= LOW:
        down_conditions += 1
        expl_down.append(f"pct_above_ma={pct_ma:.2f}")
    if adv_dec is not None and adv_dec <= 0.7:
        down_conditions += 1
        expl_down.append(f"adv_decline_ratio={adv_dec:.2f}")

    if down_conditions >= 3:
        strong_down = True

    if strong_down:
        regime = "strong_downtrend"
        global_flag = "risk_off"

        avg_core = sum(core_values) / len(core_values)
        score = max(30.0, 45.0 - (MID - avg_core) * 40.0)

        msg = (
            "MARKET STRENGTH – STRONG DOWNTREND : largeur de marché dégradée, "
            "leaders en retrait et prédominance des baisses."
        )
        if nh is not None and nl is not None:
            msg += f" new_highs={nh}, new_lows={nl}."
        if nb_assets is not None:
            expl_down.append(f"nb_assets={nb_assets}")
        if expl_down:
            msg += " " + ", ".join(expl_down)

        if divergence is not None and divergence >= DIVERGENCE_HIGH:
            msg += (
                f" Toutefois, des divergences haussières apparaissent (divergence_score={divergence:.2f}) – "
                "possibles signaux de stabilisation à surveiller."
            )

        reasons.append(msg)
        return regime, global_flag, score, reasons

    # ------------------------------------------------------------------
    # 3) Cas intermédiaire : range / mixed breadth
    # ------------------------------------------------------------------
    avg_core = sum(core_values) / len(core_values)

    regime = "mixed"
    global_flag = "caution"
    score = 50.0

    msg = (
        "MARKET STRENGTH – MIXED : signaux partagés entre hausses et baisses, "
        "largeur de marché intermédiaire."
    )
    parts: List[str] = [f"avg_core={avg_core:.2f}"]
    if adv_dec is not None:
        parts.append(f"adv_decline_ratio={adv_dec:.2f}")
    if divergence is not None:
        parts.append(f"divergence_score={divergence:.2f}")
    if nb_assets is not None:
        parts.append(f"nb_assets={nb_assets}")
    msg += " " + ", ".join(parts)

    # Légère modulation du score autour de 50
    score = 50.0 + (avg_core - MID) * 10.0
    score = max(40.0, min(60.0, score))

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


def build_market_strength_state(
    data_dir: Path,
    env: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de Market Strength à partir de :

    data/analysis/market_strength.json
    """

    src_file = data_dir / "analysis" / "market_strength.json"
    raw = load_json_file(src_file, default={})

    metrics = load_market_strength_metrics(raw)
    regime, global_flag, score, reasons = infer_market_strength_regime_and_score(
        metrics
    )

    now_ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    state: Dict[str, Any] = {
        "timestamp": now_ts,
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": {
            "breadth_score": metrics.breadth_score,
            "leadership_score": metrics.leadership_score,
            "high_low_score": metrics.high_low_score,
            "momentum_breadth_score": metrics.momentum_breadth_score,
            "divergence_score": metrics.divergence_score,
            "adv_decline_ratio": metrics.adv_decline_ratio,
            "pct_above_ma": metrics.pct_above_ma,
            "nb_new_highs": metrics.nb_new_highs,
            "nb_new_lows": metrics.nb_new_lows,
            "nb_assets": metrics.nb_assets,
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
        "[market_strength_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_market_strength_state(data_dir=data_dir, env=env)

    logger.info(
        "[market_strength_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f",
        env,
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    out_file = data_dir / "analysis" / "market_strength_engine_pro.json"
    save_json_file(out_file, state)
    logger.info(
        "[market_strength_engine_pro] market_strength_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    try:
        publish_event(
            "market.strength.state",
            "market_strength_engine_pro",
            severity=severity,
            payload=state,
        )
        logger.info(
            "[market_strength_engine_pro] Event market.strength.state publié "
            "(severity=%s, score=%.2f)",
            severity,
            state.get("score"),
        )
    except Exception as exc:  # pragma: no cover
        logger.error(
            "[market_strength_engine_pro] Impossible de publier l'event "
            "market.strength.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
