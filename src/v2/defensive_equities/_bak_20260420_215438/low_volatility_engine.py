"""
NSC - Defensive Equities - Low Volatility Engine

V1.5 :
- charge defensive_screened_universe.json
- calcule un low_vol_score structuré
- produit low_volatility_scores.json

Version V2-ready :
- structure stable
- pourra être enrichie plus tard avec vol/beta/drawdown/downside deviation réels
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
LOW_VOLATILITY_SCORES_PATH = DATA_DIR / "low_volatility_scores.json"
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


def get_base_low_vol_profile(asset: Dict[str, Any]) -> Dict[str, float]:
    asset_type = str(asset.get("type", "")).lower()
    sector = str(asset.get("sector", "")).lower()
    region = str(asset.get("region", "")).upper()
    ticker = str(asset.get("ticker", "")).upper()

    inverse_volatility_score = 68.0
    beta_score = 68.0
    drawdown_score = 68.0
    downside_deviation_score = 68.0

    if asset_type == "etf":
        inverse_volatility_score = 78.0
        beta_score = 77.0
        drawdown_score = 77.0
        downside_deviation_score = 78.0

    if sector in {"consumer_staples", "consumer_defensive"}:
        inverse_volatility_score += 11
        beta_score += 10
        drawdown_score += 8
        downside_deviation_score += 10

    elif sector == "healthcare":
        inverse_volatility_score += 8
        beta_score += 8
        drawdown_score += 7
        downside_deviation_score += 8

    elif sector == "utilities":
        inverse_volatility_score += 12
        beta_score += 11
        drawdown_score += 8
        downside_deviation_score += 11

    elif sector == "infrastructure":
        inverse_volatility_score += 9
        beta_score += 8
        drawdown_score += 7
        downside_deviation_score += 8

    elif sector == "minimum_volatility":
        inverse_volatility_score += 14
        beta_score += 13
        drawdown_score += 10
        downside_deviation_score += 13

    elif sector == "dividend_growth":
        inverse_volatility_score += 9
        beta_score += 8
        drawdown_score += 7
        downside_deviation_score += 8

    elif sector == "luxury":
        inverse_volatility_score -= 4
        beta_score -= 4
        drawdown_score -= 5
        downside_deviation_score -= 4

    elif sector == "industrial_gas":
        inverse_volatility_score += 4
        beta_score += 4
        drawdown_score += 3
        downside_deviation_score += 4

    elif sector == "technology":
        inverse_volatility_score -= 6
        beta_score -= 7
        drawdown_score -= 7
        downside_deviation_score -= 6

    if region == "EU":
        drawdown_score += 1
    elif region == "US":
        beta_score += 1

    premium_low_vol_tickers = {"PG", "KO", "PEP", "JNJ", "WMT", "USMV", "VIG", "XLV", "XLP", "VDC", "DUK", "SO"}
    if ticker in premium_low_vol_tickers:
        inverse_volatility_score += 2
        beta_score += 2
        drawdown_score += 2
        downside_deviation_score += 2

    return {
        "inverse_volatility_score": clamp_score(inverse_volatility_score),
        "beta_score": clamp_score(beta_score),
        "drawdown_score": clamp_score(drawdown_score),
        "downside_deviation_score": clamp_score(downside_deviation_score),
    }


def compute_low_volatility_score(asset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not asset.get("screen_passed", False):
        return None

    subscores = get_base_low_vol_profile(asset)

    low_vol_score = clamp_score(
        0.35 * subscores["inverse_volatility_score"]
        + 0.25 * subscores["beta_score"]
        + 0.25 * subscores["drawdown_score"]
        + 0.15 * subscores["downside_deviation_score"]
    )

    return {
        "ticker": asset.get("ticker"),
        "type": asset.get("type"),
        "sector": asset.get("sector"),
        "region": asset.get("region"),
        "low_vol_score": low_vol_score,
        "subscores": subscores,
        "score_version": "v1_5_static_profile",
    }


def compute_low_volatility_scores() -> Dict[str, Any]:
    payload = load_screened_universe()
    assets = payload.get("assets", [])

    passed_assets = [asset for asset in assets if asset.get("screen_passed", False)]
    logger.info("Calcul low volatility scores : %s actifs screen_passed.", len(passed_assets))

    scores: List[Dict[str, Any]] = []
    skipped_assets: List[Dict[str, Any]] = []

    for asset in assets:
        result = compute_low_volatility_score(asset)
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


def save_low_volatility_scores(output: Dict[str, Any]) -> None:
    save_json_file(LOW_VOLATILITY_SCORES_PATH, output)
    logger.info("Low volatility scores sauvegardés : %s", LOW_VOLATILITY_SCORES_PATH)


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage low_volatility_engine ===")

    output = compute_low_volatility_scores()
    save_low_volatility_scores(output)

    logger.info(
        "Low volatility engine terminé | scored_assets_count=%s | skipped_assets_count=%s",
        output.get("scored_assets_count", 0),
        output.get("skipped_assets_count", 0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "scored_assets_count": output.get("scored_assets_count", 0),
        "skipped_assets_count": output.get("skipped_assets_count", 0),
        "output_file": str(LOW_VOLATILITY_SCORES_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final low_volatility_engine : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans low_volatility_engine : %s", e)
        raise
