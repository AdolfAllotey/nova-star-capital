# src/v2/analysis/dollar_regime_engine.py

from __future__ import annotations
from datetime import datetime, timezone
from src.v2.utils.file_utils import save_json_file, load_json_file
from src.v2.utils.logger import get_logger
import os

logger = get_logger("dollar_regime_engine")


def _now_utc_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def main() -> None:
    """
    Dollar (USD / DXY proxy) Regime Engine

    Objectif:
    - Qualifier la force du dollar
    - Aider la lecture Risk-On / Risk-Off
    - Alimenter correlation_regime_engine_pro

    Sortie:
    data/analysis/dollar_regime_engine.json
    """

    data_dir = os.environ.get("NSC_DATA_DIR", "data")
    out_path = f"{data_dir}/analysis/dollar_regime_engine.json"

    logger.info("[dollar_regime_engine] start")

    # --- INPUTS (proxy simples & robustes) ---
    # On utilise des outputs existants si disponibles
    market_regime = load_json_file(
        f"{data_dir}/analysis/market_regime_detector.json", default={}
    )
    correlation_regime = load_json_file(
        f"{data_dir}/analysis/correlation_regime_engine_pro.json", default={}
    )

    btc_trend = market_regime.get("regime", "neutral")
    corr_flag = correlation_regime.get("regime", "neutral")

    # --- LOGIQUE ---
    score = 50
    regime = "neutral"
    trend = "flat"
    volatility = "normal"

    # Heuristique simple mais efficace
    if btc_trend in ("bear", "risk_off"):
        score += 20
        trend = "up"

    if corr_flag in ("high_corr", "caution"):
        score += 10

    if score >= 65:
        regime = "strong_usd"
    elif score <= 35:
        regime = "weak_usd"

    confidence = round(min(abs(score - 50) / 50, 1.0), 2)

    payload = {
        "timestamp": _now_utc_iso(),
        "source": "dollar_regime_engine",
        "regime": regime,
        "score": score,
        "signals": {
            "trend": trend,
            "volatility": volatility,
        },
        "confidence": confidence,
    }

    save_json_file(out_path, payload)

    logger.info(
        "[dollar_regime_engine] regime=%s score=%s confidence=%s",
        regime,
        score,
        confidence,
    )
