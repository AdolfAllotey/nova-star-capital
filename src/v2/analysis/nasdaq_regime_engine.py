"""
nasdaq_regime_engine.py
-----------------------
Analyse du régime Nasdaq (risk_on / neutral / risk_off)
Moteur READ-ONLY (aucun veto, aucun sizing).
Utilisé comme signal macro explicatif.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import math

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import save_json_file

logger = get_logger("nasdaq_regime_engine")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = ANALYSIS_DIR / "nasdaq_regime_engine.json"


def _now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mock_nasdaq_data():
    """
    TEMPORAIRE (préprod) :
    simulacre de signaux Nasdaq.
    Sera remplacé par un fetch réel (QQQ / ^NDX).
    """
    return {
        "ma50": 100,
        "ma200": 105,
        "price": 98,
        "atr_pct": 2.4,
    }


def _compute_regime(data: dict):
    price = data["price"]
    ma50 = data["ma50"]
    ma200 = data["ma200"]
    atr_pct = data["atr_pct"]

    trend = "flat"
    if ma50 > ma200:
        trend = "up"
    elif ma50 < ma200:
        trend = "down"

    if trend == "down" and price < ma50:
        regime = "risk_off"
        score = 30
    elif trend == "up" and price > ma50:
        regime = "risk_on"
        score = 70
    else:
        regime = "neutral"
        score = 50

    volatility = "normal"
    if atr_pct > 3:
        volatility = "high"
    elif atr_pct < 1.5:
        volatility = "low"

    confidence = round(min(1.0, abs(ma50 - ma200) / ma200), 2)

    return {
        "regime": regime,
        "score": score,
        "signals": {
            "trend": trend,
            "volatility": volatility,
        },
        "confidence": confidence,
    }


def main():
    logger.info("[nasdaq_regime_engine] start")

    data = _mock_nasdaq_data()
    result = _compute_regime(data)

    payload = {
        "timestamp": _now_utc(),
        "source": "nasdaq_regime_engine",
        **result,
    }

    save_json_file(str(OUTPUT_FILE), payload)

    logger.info(
        "[nasdaq_regime_engine] regime=%s score=%s confidence=%s",
        payload["regime"],
        payload["score"],
        payload["confidence"],
    )


if __name__ == "__main__":
    main()
