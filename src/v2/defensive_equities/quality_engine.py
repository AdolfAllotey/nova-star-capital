"""
NSC - Defensive Equities - Quality Engine

V1.5 :
- charge defensive_screened_universe.json
- calcule un quality_score simple mais structuré
- produit quality_scores.json

Cette version est V2-ready :
- structure de sous-scores stable
- possibilité d'injecter plus tard de vraies données fondamentales
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
QUALITY_SCORES_PATH = DATA_DIR / "quality_scores.json"
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


def get_base_quality_profile(asset: Dict[str, Any]) -> Dict[str, float]:
    """
    Profil V1.5 basé sur type / secteur / région.
    Plus tard, ces scores seront remplacés ou enrichis par de vraies métriques.
    """
    asset_type = str(asset.get("type", "")).lower()
    sector = str(asset.get("sector", "")).lower()
    region = str(asset.get("region", "")).upper()
    ticker = str(asset.get("ticker", "")).upper()

    roic_score = 70.0
    operating_margin_score = 70.0
    debt_score = 70.0
    interest_coverage_score = 70.0
    profitability_stability_score = 70.0

    if asset_type == "etf":
        roic_score = 75.0
        operating_margin_score = 75.0
        debt_score = 80.0
        interest_coverage_score = 80.0
        profitability_stability_score = 78.0

    if sector in {"consumer_staples", "consumer_defensive"}:
        roic_score += 8
        operating_margin_score += 7
        debt_score += 4
        interest_coverage_score += 5
        profitability_stability_score += 8

    elif sector == "healthcare":
        roic_score += 7
        operating_margin_score += 6
        debt_score += 3
        interest_coverage_score += 5
        profitability_stability_score += 7

    elif sector == "utilities":
        roic_score += 2
        operating_margin_score += 2
        debt_score -= 3
        interest_coverage_score += 1
        profitability_stability_score += 5

    elif sector == "infrastructure":
        roic_score += 5
        operating_margin_score += 4
        debt_score += 1
        interest_coverage_score += 3
        profitability_stability_score += 6

    elif sector == "minimum_volatility":
        roic_score += 4
        operating_margin_score += 4
        debt_score += 6
        interest_coverage_score += 6
        profitability_stability_score += 7

    elif sector == "dividend_growth":
        roic_score += 5
        operating_margin_score += 5
        debt_score += 5
        interest_coverage_score += 5
        profitability_stability_score += 6

    elif sector == "luxury":
        roic_score += 6
        operating_margin_score += 7
        debt_score += 2
        interest_coverage_score += 4
        profitability_stability_score += 4

    elif sector == "industrial_gas":
        roic_score += 7
        operating_margin_score += 7
        debt_score += 3
        interest_coverage_score += 5
        profitability_stability_score += 6

    elif sector == "technology":
        roic_score += 5
        operating_margin_score += 6
        debt_score += 4
        interest_coverage_score += 4
        profitability_stability_score += 3

    if region == "EU":
        debt_score += 1
        profitability_stability_score += 1
    elif region == "US":
        roic_score += 1
        operating_margin_score += 1

    # petits ajustements ticker-specific V1.5
    premium_tickers = set(load_defensive_universe(logger=logger))
    if ticker in premium_tickers:
        roic_score += 2
        operating_margin_score += 2
        profitability_stability_score += 2

    return {
        "roic_score": clamp_score(roic_score),
        "operating_margin_score": clamp_score(operating_margin_score),
        "debt_score": clamp_score(debt_score),
        "interest_coverage_score": clamp_score(interest_coverage_score),
        "profitability_stability_score": clamp_score(profitability_stability_score),
    }


def compute_quality_score(asset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not asset.get("screen_passed", False):
        return None

    subscores = get_base_quality_profile(asset)

    quality_score = clamp_score(
        0.30 * subscores["roic_score"]
        + 0.25 * subscores["operating_margin_score"]
        + 0.20 * subscores["debt_score"]
        + 0.15 * subscores["interest_coverage_score"]
        + 0.10 * subscores["profitability_stability_score"]
    )

    return {
        "ticker": asset.get("ticker"),
        "type": asset.get("type"),
        "sector": asset.get("sector"),
        "region": asset.get("region"),
        "quality_score": quality_score,
        "subscores": subscores,
        "score_version": "v1_5_static_profile",
    }


def compute_quality_scores() -> Dict[str, Any]:
    payload = load_screened_universe()
    assets = payload.get("assets", [])

    passed_assets = [asset for asset in assets if asset.get("screen_passed", False)]
    logger.info("Calcul quality scores : %s actifs screen_passed.", len(passed_assets))

    scores: List[Dict[str, Any]] = []
    skipped_assets: List[Dict[str, Any]] = []

    for asset in assets:
        result = compute_quality_score(asset)
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


def save_quality_scores(output: Dict[str, Any]) -> None:
    save_json_file(QUALITY_SCORES_PATH, output)
    logger.info("Quality scores sauvegardés : %s", QUALITY_SCORES_PATH)


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage quality_engine ===")

    output = compute_quality_scores()
    save_quality_scores(output)

    logger.info(
        "Quality engine terminé | scored_assets_count=%s | skipped_assets_count=%s",
        output.get("scored_assets_count", 0),
        output.get("skipped_assets_count", 0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "scored_assets_count": output.get("scored_assets_count", 0),
        "skipped_assets_count": output.get("skipped_assets_count", 0),
        "output_file": str(QUALITY_SCORES_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final quality_engine : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans quality_engine : %s", e)
        raise
