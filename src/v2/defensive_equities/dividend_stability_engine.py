"""
NSC - Defensive Equities - Dividend Stability Engine

V1.5 :
- charge defensive_screened_universe.json
- calcule un dividend_score structuré
- produit dividend_scores.json

Version V2-ready :
- structure stable
- pourra être enrichie plus tard avec historique réel des dividendes,
  payout ratio, FCF coverage, régularité de distribution, etc.
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
try:
    from .common import DATA_DIR, LOG_DIR
except ImportError:
    from common import DATA_DIR, LOG_DIR
from typing import Any, Dict, List, Optional

from src.v2.defensive_equities.common import load_defensive_universe

BRICK_NAME = "defensive_equities"
DEFAULT_ENV = os.getenv("NSC_ENV", "PREPROD")


SCREENED_UNIVERSE_PATH = DATA_DIR / "defensive_screened_universe.json"
DIVIDEND_SCORES_PATH = DATA_DIR / "dividend_scores.json"
LOG_PATH = LOG_DIR / "defensive_equities.log"


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json_file(path: Path, default: Optional[Any] = None) -> Any:
    if not path.exists():
        return deepcopy(default)

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Erreur lecture JSON %s : %s", path, e)
        return deepcopy(default)


def save_json_file(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Erreur sauvegarde JSON %s : %s", path, e)
        raise


def load_screened_universe() -> Dict[str, Any]:
    default_payload: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": DEFAULT_ENV,
        "generated_at": None,
        "input_universe_size": 0,
        "screened_universe_size": 0,
        "excluded_assets_count": 0,
        "assets": [],
    }

    payload = load_json_file(SCREENED_UNIVERSE_PATH, default=default_payload)

    if not isinstance(payload, dict):
        logger.warning("Screened universe invalide : format non dict.")
        return default_payload

    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        logger.warning("Screened universe invalide : 'assets' non list.")
        payload["assets"] = []

    return payload


def clamp_score(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, value)), 2)


def get_base_dividend_profile(asset: Dict[str, Any]) -> Dict[str, float]:
    asset_type = str(asset.get("type", "")).lower()
    sector = str(asset.get("sector", "")).lower()
    region = str(asset.get("region", "")).upper()
    ticker = str(asset.get("ticker", "")).upper()

    dividend_history_score = 66.0
    dividend_growth_score = 66.0
    payout_sustainability_score = 66.0
    fcf_coverage_score = 66.0
    distribution_regularity_score = 66.0

    if asset_type == "etf":
        dividend_history_score = 75.0
        dividend_growth_score = 73.0
        payout_sustainability_score = 78.0
        fcf_coverage_score = 78.0
        distribution_regularity_score = 77.0

    if sector in {"consumer_staples", "consumer_defensive"}:
        dividend_history_score += 12
        dividend_growth_score += 9
        payout_sustainability_score += 8
        fcf_coverage_score += 8
        distribution_regularity_score += 10

    elif sector == "healthcare":
        dividend_history_score += 8
        dividend_growth_score += 7
        payout_sustainability_score += 7
        fcf_coverage_score += 7
        distribution_regularity_score += 7

    elif sector == "utilities":
        dividend_history_score += 10
        dividend_growth_score += 5
        payout_sustainability_score += 4
        fcf_coverage_score += 4
        distribution_regularity_score += 9

    elif sector == "infrastructure":
        dividend_history_score += 8
        dividend_growth_score += 6
        payout_sustainability_score += 5
        fcf_coverage_score += 5
        distribution_regularity_score += 7

    elif sector == "minimum_volatility":
        dividend_history_score += 7
        dividend_growth_score += 6
        payout_sustainability_score += 7
        fcf_coverage_score += 7
        distribution_regularity_score += 7

    elif sector == "dividend_growth":
        dividend_history_score += 10
        dividend_growth_score += 11
        payout_sustainability_score += 8
        fcf_coverage_score += 8
        distribution_regularity_score += 9

    elif sector == "luxury":
        dividend_history_score += 5
        dividend_growth_score += 5
        payout_sustainability_score += 4
        fcf_coverage_score += 5
        distribution_regularity_score += 4

    elif sector == "industrial_gas":
        dividend_history_score += 8
        dividend_growth_score += 8
        payout_sustainability_score += 7
        fcf_coverage_score += 7
        distribution_regularity_score += 7

    elif sector == "technology":
        dividend_history_score -= 2
        dividend_growth_score += 1
        payout_sustainability_score += 0
        fcf_coverage_score += 1
        distribution_regularity_score -= 2

    if region == "EU":
        dividend_history_score += 1
        distribution_regularity_score += 1

    premium_dividend_tickers = set(load_defensive_universe(logger=logger))
    if ticker in premium_dividend_tickers:
        dividend_history_score += 2
        dividend_growth_score += 2
        payout_sustainability_score += 2
        fcf_coverage_score += 2
        distribution_regularity_score += 2

    return {
        "dividend_history_score": clamp_score(dividend_history_score),
        "dividend_growth_score": clamp_score(dividend_growth_score),
        "payout_sustainability_score": clamp_score(payout_sustainability_score),
        "fcf_coverage_score": clamp_score(fcf_coverage_score),
        "distribution_regularity_score": clamp_score(distribution_regularity_score),
    }


def compute_dividend_score(asset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not asset.get("screen_passed", False):
        return None

    subscores = get_base_dividend_profile(asset)

    dividend_score = clamp_score(
        0.25 * subscores["dividend_history_score"]
        + 0.20 * subscores["dividend_growth_score"]
        + 0.20 * subscores["payout_sustainability_score"]
        + 0.20 * subscores["fcf_coverage_score"]
        + 0.15 * subscores["distribution_regularity_score"]
    )

    return {
        "ticker": asset.get("ticker"),
        "type": asset.get("type"),
        "sector": asset.get("sector"),
        "region": asset.get("region"),
        "dividend_score": dividend_score,
        "subscores": subscores,
        "score_version": "v1_5_static_profile",
    }


def compute_dividend_scores() -> Dict[str, Any]:
    payload = load_screened_universe()
    assets = payload.get("assets", [])

    passed_assets = [asset for asset in assets if asset.get("screen_passed", False)]
    logger.info("Calcul dividend scores : %s actifs screen_passed.", len(passed_assets))

    scores: List[Dict[str, Any]] = []
    skipped_assets: List[Dict[str, Any]] = []

    for asset in assets:
        result = compute_dividend_score(asset)
        if result is None:
            skipped_assets.append({
                "ticker": asset.get("ticker"),
                "reason": "screen_not_passed",
            })
            continue
        scores.append(result)

    output: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": payload.get("env", DEFAULT_ENV),
        "generated_at": utc_now_iso(),
        "input_assets_count": len(assets),
        "scored_assets_count": len(scores),
        "skipped_assets_count": len(skipped_assets),
        "scores": scores,
        "skipped_assets": skipped_assets,
    }

    return output


def save_dividend_scores(output: Dict[str, Any]) -> None:
    save_json_file(DIVIDEND_SCORES_PATH, output)
    logger.info("Dividend scores sauvegardés : %s", DIVIDEND_SCORES_PATH)


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage dividend_stability_engine ===")

    output = compute_dividend_scores()
    save_dividend_scores(output)

    logger.info(
        "Dividend stability engine terminé | scored_assets_count=%s | skipped_assets_count=%s",
        output.get("scored_assets_count", 0),
        output.get("skipped_assets_count", 0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "scored_assets_count": output.get("scored_assets_count", 0),
        "skipped_assets_count": output.get("skipped_assets_count", 0),
        "output_file": str(DIVIDEND_SCORES_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final dividend_stability_engine : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans dividend_stability_engine : %s", e)
        raise
