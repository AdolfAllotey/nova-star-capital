"""
NSC - Defensive Equities - Defensive Score Engine

V1.5 :
- charge quality_scores.json
- charge earnings_stability_scores.json
- charge low_volatility_scores.json
- charge dividend_scores.json
- fusionne les scores par ticker
- ajoute un liquidity_score simple V1.5
- calcule defensive_score
- produit defensive_scores.json
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

QUALITY_SCORES_PATH = DATA_DIR / "quality_scores.json"
EARNINGS_STABILITY_SCORES_PATH = DATA_DIR / "earnings_stability_scores.json"
LOW_VOLATILITY_SCORES_PATH = DATA_DIR / "low_volatility_scores.json"
DIVIDEND_SCORES_PATH = DATA_DIR / "dividend_scores.json"
DEFENSIVE_SCORES_PATH = DATA_DIR / "defensive_scores.json"
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


def clamp_score(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, value)), 2)


def build_default_payload() -> Dict[str, Any]:
    return {
        "brick": BRICK_NAME,
        "env": DEFAULT_ENV,
        "generated_at": None,
        "scores": [],
    }


def load_quality_scores() -> Dict[str, Any]:
    return load_json_file(QUALITY_SCORES_PATH, default=build_default_payload())


def load_earnings_stability_scores() -> Dict[str, Any]:
    return load_json_file(EARNINGS_STABILITY_SCORES_PATH, default=build_default_payload())


def load_low_volatility_scores() -> Dict[str, Any]:
    return load_json_file(LOW_VOLATILITY_SCORES_PATH, default=build_default_payload())


def load_dividend_scores() -> Dict[str, Any]:
    return load_json_file(DIVIDEND_SCORES_PATH, default=build_default_payload())


def index_scores_by_ticker(payload: Dict[str, Any], score_field: str) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}

    scores = payload.get("scores", [])
    if not isinstance(scores, list):
        return indexed

    for item in scores:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker", "")).strip().upper()
        if not ticker:
            continue
        if score_field not in item:
            continue
        indexed[ticker] = item

    return indexed


def compute_liquidity_score(merged_asset: Dict[str, Any]) -> float:
    """
    V1.5 : score simple basé sur type / région / secteur.
    Plus tard, on branchera avg volume / dollar volume / spread / ADV.
    """
    asset_type = str(merged_asset.get("type", "")).lower()
    region = str(merged_asset.get("region", "")).upper()
    sector = str(merged_asset.get("sector", "")).lower()
    ticker = str(merged_asset.get("ticker", "")).upper()

    score = 78.0

    if asset_type == "etf":
        score += 10

    if region == "US":
        score += 7
    elif region == "EU":
        score += 3
    elif region == "CA":
        score += 2

    if sector in {"consumer_staples", "healthcare", "minimum_volatility", "dividend_growth"}:
        score += 2

    highly_liquid_tickers = {
        "PG", "KO", "PEP", "WMT", "COST", "JNJ", "UNH", "MRK",
        "LLY", "USMV", "VIG", "XLV", "XLP", "VDC", "ASML"
    }
    if ticker in highly_liquid_tickers:
        score += 3

    return clamp_score(score)


def merge_scores_by_ticker() -> Dict[str, Any]:
    quality_payload = load_quality_scores()
    earnings_payload = load_earnings_stability_scores()
    low_vol_payload = load_low_volatility_scores()
    dividend_payload = load_dividend_scores()

    quality_idx = index_scores_by_ticker(quality_payload, "quality_score")
    earnings_idx = index_scores_by_ticker(earnings_payload, "earnings_stability_score")
    low_vol_idx = index_scores_by_ticker(low_vol_payload, "low_vol_score")
    dividend_idx = index_scores_by_ticker(dividend_payload, "dividend_score")

    all_tickers = sorted(
        set(quality_idx.keys())
        & set(earnings_idx.keys())
        & set(low_vol_idx.keys())
        & set(dividend_idx.keys())
    )

    merged_scores: List[Dict[str, Any]] = []
    missing_tickers: Dict[str, List[str]] = {}

    all_seen_tickers = sorted(
        set(quality_idx.keys())
        | set(earnings_idx.keys())
        | set(low_vol_idx.keys())
        | set(dividend_idx.keys())
    )

    for ticker in all_seen_tickers:
        missing = []
        if ticker not in quality_idx:
            missing.append("quality_score")
        if ticker not in earnings_idx:
            missing.append("earnings_stability_score")
        if ticker not in low_vol_idx:
            missing.append("low_vol_score")
        if ticker not in dividend_idx:
            missing.append("dividend_score")
        if missing:
            missing_tickers[ticker] = missing

    for ticker in all_tickers:
        q = quality_idx[ticker]
        e = earnings_idx[ticker]
        lv = low_vol_idx[ticker]
        d = dividend_idx[ticker]

        merged_asset: Dict[str, Any] = {
            "ticker": ticker,
            "type": q.get("type", e.get("type", lv.get("type", d.get("type")))),
            "sector": q.get("sector", e.get("sector", lv.get("sector", d.get("sector")))),
            "region": q.get("region", e.get("region", lv.get("region", d.get("region")))),
            "quality_score": q.get("quality_score"),
            "earnings_stability_score": e.get("earnings_stability_score"),
            "low_vol_score": lv.get("low_vol_score"),
            "dividend_score": d.get("dividend_score"),
        }

        liquidity_score = compute_liquidity_score(merged_asset)
        merged_asset["liquidity_score"] = liquidity_score

        defensive_score = clamp_score(
            0.30 * float(merged_asset["quality_score"])
            + 0.25 * float(merged_asset["earnings_stability_score"])
            + 0.20 * float(merged_asset["low_vol_score"])
            + 0.15 * float(merged_asset["dividend_score"])
            + 0.10 * float(liquidity_score)
        )

        merged_asset["defensive_score"] = defensive_score
        merged_asset["score_version"] = "v1_5_composite"
        merged_scores.append(merged_asset)

    return {
        "brick": BRICK_NAME,
        "env": DEFAULT_ENV,
        "generated_at": utc_now_iso(),
        "scored_assets_count": len(merged_scores),
        "missing_tickers_count": len(missing_tickers),
        "missing_tickers": missing_tickers,
        "scores": sorted(
            merged_scores,
            key=lambda x: x.get("defensive_score", 0.0),
            reverse=True
        ),
    }


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage defensive_score_engine ===")

    output = merge_scores_by_ticker()
    save_json_file(DEFENSIVE_SCORES_PATH, output)

    logger.info(
        "Defensive score engine terminé | scored_assets_count=%s | missing_tickers_count=%s",
        output.get("scored_assets_count", 0),
        output.get("missing_tickers_count", 0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "scored_assets_count": output.get("scored_assets_count", 0),
        "missing_tickers_count": output.get("missing_tickers_count", 0),
        "output_file": str(DEFENSIVE_SCORES_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final defensive_score_engine : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans defensive_score_engine : %s", e)
        raise
