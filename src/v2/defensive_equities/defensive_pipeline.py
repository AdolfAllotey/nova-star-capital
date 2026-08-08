"""
NSC - Defensive Equities - Pipeline V1.5 complet
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from common import BRICK_NAME, LOG_DIR, LOG_PATH
from defensive_universe_builder import run as run_universe_builder
from defensive_screener import run as run_screener
from quality_engine import run as run_quality_engine
from earnings_stability_engine import run as run_earnings_stability_engine
from low_volatility_engine import run as run_low_volatility_engine
from dividend_stability_engine import run as run_dividend_engine
from defensive_score_engine import run as run_defensive_score_engine
from defensive_allocator import run as run_defensive_allocator
from defensive_signal_engine import run as run_defensive_signal_engine


def setup_logger(name: str = BRICK_NAME) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


logger = setup_logger()


def run_defensive_pipeline() -> Dict[str, Any]:
    logger.info("=== Démarrage defensive_pipeline V1.5 complet ===")

    universe_result = run_universe_builder()
    screener_result = run_screener()
    quality_result = run_quality_engine()
    earnings_stability_result = run_earnings_stability_engine()
    low_volatility_result = run_low_volatility_engine()
    dividend_result = run_dividend_engine()
    defensive_score_result = run_defensive_score_engine()
    defensive_allocation_result = run_defensive_allocator()
    defensive_signal_result = run_defensive_signal_engine()

    result = {
        "status": "ok",
        "brick": BRICK_NAME,
        "universe_result": universe_result,
        "screener_result": screener_result,
        "quality_result": quality_result,
        "earnings_stability_result": earnings_stability_result,
        "low_volatility_result": low_volatility_result,
        "dividend_result": dividend_result,
        "defensive_score_result": defensive_score_result,
        "defensive_allocation_result": defensive_allocation_result,
        "defensive_signal_result": defensive_signal_result,
    }

    logger.info("Pipeline défensif V1.5 complet terminé : %s", result)
    return result


if __name__ == "__main__":
    try:
        final_result = run_defensive_pipeline()
        logger.info("Résultat final pipeline : %s", final_result)
    except Exception as e:
        logger.exception("Erreur critique dans defensive_pipeline : %s", e)
        raise
