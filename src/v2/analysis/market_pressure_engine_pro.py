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
class MarketPressureMetrics:
    """
    Métriques de pression de marché (flux agressifs, absorption, déséquilibre).

    JSON attendu dans data/analysis/market_pressure.json (format souple) :

    {
      "buy_pressure_score": 0.6,           # 0–1 (pression acheteuse agrégée)
      "sell_pressure_score": 0.3,          # 0–1 (pression vendeuse agrégée)
      "pressure_imbalance_score": 0.7,     # 0–1 (déséquilibre global)
      "absorption_score": 0.4,             # 0–1 (absorption des flux agressifs)
      "exhaustion_score": 0.2,             # 0–1 (signes d'épuisement)
      "aggressive_buy_ratio": 0.65,        # 0–1 (% agressions côté achat)
      "aggressive_sell_ratio": 0.25,       # 0–1 (% agressions côté vente)
      "nb_assets": 120                     # nb d'actifs analysés
    }
    """

    buy_pressure_score: Optional[float]
    sell_pressure_score: Optional[float]
    pressure_imbalance_score: Optional[float]
    absorption_score: Optional[float]
    exhaustion_score: Optional[float]
    aggressive_buy_ratio: Optional[float]
    aggressive_sell_ratio: Optional[float]
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


def load_market_pressure_metrics(raw: Any) -> MarketPressureMetrics:
    if not isinstance(raw, dict):
        raw = {}

    return MarketPressureMetrics(
        buy_pressure_score=_get_float(raw.get("buy_pressure_score")),
        sell_pressure_score=_get_float(raw.get("sell_pressure_score")),
        pressure_imbalance_score=_get_float(raw.get("pressure_imbalance_score")),
        absorption_score=_get_float(raw.get("absorption_score")),
        exhaustion_score=_get_float(raw.get("exhaustion_score")),
        aggressive_buy_ratio=_get_float(raw.get("aggressive_buy_ratio")),
        aggressive_sell_ratio=_get_float(raw.get("aggressive_sell_ratio")),
        nb_assets=_get_int(raw.get("nb_assets")),
    )


# ---------------------------------------------------------------------------
# Logic Market Pressure
# ---------------------------------------------------------------------------

def infer_market_pressure_regime_and_score(
    m: MarketPressureMetrics,
) -> Tuple[str, str, float, List[str]]:
    """
    Déduit un régime de Market Pressure + flag global + score NSC.

    Intuition :

    - Pression vendeuse agressive, déséquilibre fort → "sell_pressure_dominant"
      → global_flag = "risk_off" (contexte défensif).
    - Pression acheteuse agressive, cohérente → "buy_pressure_dominant"
      → global_flag = "supportive" (risk_on, mais c'est un bloc du meta-score).
    - Déséquilibre modéré / flux mitigés → "mixed_pressure"
      → global_flag = "caution".
    - Pas de signal → "unknown" / neutre.
    """

    reasons: List[str] = []

    core_values = [
        v
        for v in (
            m.buy_pressure_score,
            m.sell_pressure_score,
            m.pressure_imbalance_score,
            m.aggressive_buy_ratio,
            m.aggressive_sell_ratio,
        )
        if v is not None
    ]
    if not core_values:
        reasons.append("Aucune donnée de Market Pressure exploitable – score neutre.")
        return "unknown", "caution", 50.0, reasons

    # Seuils
    HIGH = 0.65
    MID = 0.45

    regime = "unknown"
    global_flag = "caution"
    score = 50.0

    buy_p = m.buy_pressure_score
    sell_p = m.sell_pressure_score
    imb = m.pressure_imbalance_score
    abs_score = m.absorption_score
    exh_score = m.exhaustion_score
    aggr_buy = m.aggressive_buy_ratio
    aggr_sell = m.aggressive_sell_ratio
    nb_assets = m.nb_assets

    # 1) Cas extrême – sell pressure dominante (context risk_off)
    #    - forte pression vendeuse + agressivité vendeuse
    #    - ou déséquilibre global important côté vente
    sell_dominant = False
    expl_parts_sell: List[str] = []

    if sell_p is not None and sell_p >= HIGH:
        sell_dominant = True
        expl_parts_sell.append(f"sell_pressure_score={sell_p:.2f}")
    if aggr_sell is not None and aggr_sell >= HIGH:
        sell_dominant = True
        expl_parts_sell.append(f"aggressive_sell_ratio={aggr_sell:.2f}")
    if imb is not None and imb >= HIGH and (sell_p or 0) >= (buy_p or 0):
        sell_dominant = True
        expl_parts_sell.append(f"pressure_imbalance_score={imb:.2f}")

    if sell_dominant:
        regime = "sell_pressure_dominant"
        global_flag = "risk_off"
        score = 42.0

        msg = (
            "MARKET PRESSURE – SELL DOMINANT : flux vendeurs agressifs et "
            "déséquilibre net côté offre – conditions défensives."
        )
        if nb_assets is not None:
            expl_parts_sell.append(f"nb_assets={nb_assets}")
        if expl_parts_sell:
            msg += " " + ", ".join(expl_parts_sell)

        # Exhaustion / absorption peuvent nuancer le message.
        if abs_score is not None and abs_score >= MID:
            msg += (
                f" Absorption significative détectée (absorption_score={abs_score:.2f}) – "
                "possibles défenses des acheteurs sur certains niveaux."
            )
        if exh_score is not None and exh_score >= MID:
            msg += (
                f" Signes d'épuisement vendeurs (exhaustion_score={exh_score:.2f}) – "
                "risque de squeezes ou de rebonds violents."
            )

        reasons.append(msg)
        return regime, global_flag, score, reasons

    # 2) Cas extrême – buy pressure dominante (context supportive)
    buy_dominant = False
    expl_parts_buy: List[str] = []

    if buy_p is not None and buy_p >= HIGH:
        buy_dominant = True
        expl_parts_buy.append(f"buy_pressure_score={buy_p:.2f}")
    if aggr_buy is not None and aggr_buy >= HIGH:
        buy_dominant = True
        expl_parts_buy.append(f"aggressive_buy_ratio={aggr_buy:.2f}")
    if imb is not None and imb >= HIGH and (buy_p or 0) > (sell_p or 0):
        buy_dominant = True
        expl_parts_buy.append(f"pressure_imbalance_score={imb:.2f}")

    if buy_dominant:
        regime = "buy_pressure_dominant"
        global_flag = "supportive"
        score = 60.0

        msg = (
            "MARKET PRESSURE – BUY DOMINANT : flux acheteurs agressifs et "
            "déséquilibre net côté demande – conditions plutôt risk_on."
        )
        if nb_assets is not None:
            expl_parts_buy.append(f"nb_assets={nb_assets}")
        if expl_parts_buy:
            msg += " " + ", ".join(expl_parts_buy)

        # Exhaustion / absorption peuvent nuancer le message.
        if exh_score is not None and exh_score >= MID:
            msg += (
                f" Signes d'épuisement acheteurs (exhaustion_score={exh_score:.2f}) – "
                "attention aux fake breakouts."
            )
        if abs_score is not None and abs_score >= MID:
            msg += (
                f" Absorption sur les offers (absorption_score={abs_score:.2f}) – "
                "présence potentielle de gros vendeurs cachés."
            )

        reasons.append(msg)
        return regime, global_flag, score, reasons

    # 3) Déséquilibre modéré / flux mixtes → WATCH / caution
    #    On regarde surtout pressure_imbalance_score et les scores moyens.
    avg_core = sum(core_values) / len(core_values)
    if imb is not None and imb >= MID:
        regime = "mixed_pressure"
        global_flag = "caution"
        score = 47.0

        msg = (
            "MARKET PRESSURE – MIXED : déséquilibre modéré des flux acheteurs/vendeurs, "
            "avec structure de pression mitigée."
        )
        parts = [f"pressure_imbalance_score={imb:.2f}", f"avg_core={avg_core:.2f}"]
        if nb_assets is not None:
            parts.append(f"nb_assets={nb_assets}")
        msg += " " + ", ".join(parts)
        reasons.append(msg)
        return regime, global_flag, score, reasons

    # 4) Structure équilibrée → neutre / légèrement supportive
    regime = "balanced"
    global_flag = "neutral"
    score = 55.0

    msg = (
        "MARKET PRESSURE – BALANCED : équilibre global des flux acheteurs/vendeurs, "
        "pas de pression directionnelle marquée."
    )
    parts = [f"avg_core={avg_core:.2f}"]
    if nb_assets is not None:
        parts.append(f"nb_assets={nb_assets}")
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


def build_market_pressure_state(
    data_dir: Path,
    env: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de Market Pressure à partir de :

    data/analysis/market_pressure.json
    """

    src_file = data_dir / "analysis" / "market_pressure.json"
    raw = load_json_file(src_file, default={})

    metrics = load_market_pressure_metrics(raw)
    regime, global_flag, score, reasons = infer_market_pressure_regime_and_score(
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
            "buy_pressure_score": metrics.buy_pressure_score,
            "sell_pressure_score": metrics.sell_pressure_score,
            "pressure_imbalance_score": metrics.pressure_imbalance_score,
            "absorption_score": metrics.absorption_score,
            "exhaustion_score": metrics.exhaustion_score,
            "aggressive_buy_ratio": metrics.aggressive_buy_ratio,
            "aggressive_sell_ratio": metrics.aggressive_sell_ratio,
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
        "[market_pressure_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_market_pressure_state(data_dir=data_dir, env=env)

    logger.info(
        "[market_pressure_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f",
        env,
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    out_file = data_dir / "analysis" / "market_pressure_engine_pro.json"
    save_json_file(out_file, state)
    logger.info(
        "[market_pressure_engine_pro] market_pressure_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    try:
        publish_event(
            "market.pressure.state",
            "market_pressure_engine_pro",
            severity=severity,
            payload=state,
        )
        logger.info(
            "[market_pressure_engine_pro] Event market.pressure.state publié "
            "(severity=%s, score=%.2f)",
            severity,
            state.get("score"),
        )
    except Exception as exc:  # pragma: no cover
        logger.error(
            "[market_pressure_engine_pro] Impossible de publier l'event "
            "market.pressure.state : %s",
            exc,
        )


if __name__ == "__main__":
    main()
