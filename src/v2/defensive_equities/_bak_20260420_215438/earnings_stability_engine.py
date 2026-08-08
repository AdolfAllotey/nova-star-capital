"""
NSC - Defensive Equities - Earnings Stability Engine

V1.5 :
- charge defensive_screened_universe.json
- calcule un earnings_stability_score structuré
- produit earnings_stability_scores.json

Version V2-ready :
- structure stable
- pourra être enrichie plus tard avec revenue/EPS/FCF réels
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BRICK_NAME = "defensive_equities"
DEFAULT_ENV = os.getenv("NSC_ENV", "PREPROD")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "defensive"
LOG_DIR = BASE_DIR / "logs"

SCREENED_UNIVERSE_PATH = DATA_DIR / "defensive_screened_universe.json"
EARNINGS_STABILITY_SCORES_PATH = DATA_DIR / "earnings_stability_scores.json"
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


def get_base_stability_profile(asset: Dict[str, Any]) -> Dict[str, float]:
    asset_type = str(asset.get("type", "")).lower()
    sector = str(asset.get("sector", "")).lower()
    region = str(asset.get("region", "")).upper()
    ticker = str(asset.get("ticker", "")).upper()

    revenue_stability_score = 70.0
    eps_stability_score = 70.0
    fcf_stability_score = 70.0
    margin_stability_score = 70.0

    if asset_type == "etf":
        revenue_stability_score = 80.0
        eps_stability_score = 78.0
        fcf_stability_score = 80.0
        margin_stability_score = 79.0

    if sector in {"consumer_staples", "consumer_defensive"}:
        revenue_stability_score += 10
        eps_stability_score += 8
        fcf_stability_score += 8
        margin_stability_score += 8

    elif sector == "healthcare":
        revenue_stability_score += 8
        eps_stability_score += 7
        fcf_stability_score += 7
        margin_stability_score += 7

    elif sector == "utilities":
        revenue_stability_score += 8
        eps_stability_score += 5
        fcf_stability_score += 5
        margin_stability_score += 6

    elif sector == "infrastructure":
        revenue_stability_score += 7
        eps_stability_score += 6
        fcf_stability_score += 6
        margin_stability_score += 6

    elif sector == "minimum_volatility":
        revenue_stability_score += 7
        eps_stability_score += 7
        fcf_stability_score += 7
        margin_stability_score += 7

    elif sector == "dividend_growth":
        revenue_stability_score += 7
        eps_stability_score += 7
        fcf_stability_score += 7
        margin_stability_score += 6

    elif sector == "luxury":
        revenue_stability_score += 3
        eps_stability_score += 3
        fcf_stability_score += 4
        margin_stability_score += 3

    elif sector == "industrial_gas":
        revenue_stability_score += 7
        eps_stability_score += 6
        fcf_stability_score += 7
        margin_stability_score += 6

    elif sector == "technology":
        revenue_stability_score += 2
        eps_stability_score += 2
        fcf_stability_score += 4
        margin_stability_score += 2

    if region == "EU":
        revenue_stability_score += 1
        margin_stability_score += 1

    premium_tickers = {"PG", "KO", "PEP", "JNJ", "WMT", "COST", "NESN", "AI", "ROG", "USMV", "VIG", "XLV"}
    if ticker in premium_tickers:
        revenue_stability_score += 2
        eps_stability_score += 2
        fcf_stability_score += 2
        margin_stability_score += 2

    return {
        "revenue_stability_score": clamp_score(revenue_stability_score),
        "eps_stability_score": clamp_score(eps_stability_score),
        "fcf_stability_score": clamp_score(fcf_stability_score),
        "margin_stability_score": clamp_score(margin_stability_score),
    }


def compute_earnings_stability_score(asset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not asset.get("screen_passed", False):
        return None

    subscores = get_base_stability_profile(asset)

    earnings_stability_score = clamp_score(
        0.35 * subscores["revenue_stability_score"]
        + 0.25 * subscores["eps_stability_score"]
        + 0.25 * subscores["fcf_stability_score"]
        + 0.15 * subscores["margin_stability_score"]
    )

    return {
        "ticker": asset.get("ticker"),
        "type": asset.get("type"),
        "sector": asset.get("sector"),
        "region": asset.get("region"),
        "earnings_stability_score": earnings_stability_score,
        "subscores": subscores,
        "score_version": "v1_5_static_profile",
    }


def compute_earnings_stability_scores() -> Dict[str, Any]:
    payload = load_screened_universe()
    assets = payload.get("assets", [])

    passed_assets = [asset for asset in assets if asset.get("screen_passed", False)]
    logger.info("Calcul earnings stability scores : %s actifs screen_passed.", len(passed_assets))

    scores: List[Dict[str, Any]] = []
    skipped_assets: List[Dict[str, Any]] = []

    for asset in assets:
        result = compute_earnings_stability_score(asset)
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


def save_earnings_stability_scores(output: Dict[str, Any]) -> None:
    save_json_file(EARNINGS_STABILITY_SCORES_PATH, output)
    logger.info("Earnings stability scores sauvegardés : %s", EARNINGS_STABILITY_SCORES_PATH)


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage earnings_stability_engine ===")

    output = compute_earnings_stability_scores()
    save_earnings_stability_scores(output)

    logger.info(
        "Earnings stability engine terminé | scored_assets_count=%s | skipped_assets_count=%s",
        output.get("scored_assets_count", 0),
        output.get("skipped_assets_count", 0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "scored_assets_count": output.get("scored_assets_count", 0),
        "skipped_assets_count": output.get("skipped_assets_count", 0),
        "output_file": str(EARNINGS_STABILITY_SCORES_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final earnings_stability_engine : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans earnings_stability_engine : %s", e)
        raise
