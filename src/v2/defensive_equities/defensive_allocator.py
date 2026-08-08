"""
NSC - Defensive Equities - Defensive Allocator

V1.5 corrigé :
- charge defensive_scores.json
- sélectionne les meilleurs actifs
- applique des contraintes robustes :
  * 6 à 10 positions
  * max 20% par ligne
  * max 35% par secteur
  * max 40% cumulé en ETF
  * minimum 3 actions individuelles
- produit defensive_allocations.json
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

BRICK_NAME = "defensive_equities"
DEFAULT_ENV = os.getenv("NSC_ENV", "PREPROD")


DEFENSIVE_SCORES_PATH = DATA_DIR / "defensive_scores.json"
DEFENSIVE_ALLOCATIONS_PATH = DATA_DIR / "defensive_allocations.json"
LOG_PATH = LOG_DIR / "defensive_equities.log"

TARGET_EXPOSURE_DEFAULT = 0.20
MIN_POSITIONS = 6
MAX_POSITIONS = 10
MIN_STOCK_COUNT = 3
MAX_WEIGHT_PER_ASSET = 0.20
MAX_SECTOR_WEIGHT = 0.35
MAX_ETF_TOTAL_WEIGHT = 0.40


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


def clamp_weight(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return round(max(minimum, min(maximum, value)), 6)


def load_defensive_scores() -> Dict[str, Any]:
    default_payload: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": DEFAULT_ENV,
        "generated_at": None,
        "scored_assets_count": 0,
        "missing_tickers_count": 0,
        "missing_tickers": {},
        "scores": [],
    }

    payload = load_json_file(DEFENSIVE_SCORES_PATH, default=default_payload)

    if not isinstance(payload, dict):
        logger.warning("Defensive scores invalide : format non dict.")
        return default_payload

    if not isinstance(payload.get("scores", []), list):
        logger.warning("Defensive scores invalide : 'scores' non list.")
        payload["scores"] = []

    return payload


def get_target_exposure() -> float:
    return TARGET_EXPOSURE_DEFAULT


def split_assets(scores: List[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    etfs = [a for a in scores if str(a.get("type", "")).lower() == "etf"]
    stocks = [a for a in scores if str(a.get("type", "")).lower() == "stock"]
    return etfs, stocks


def select_candidates(scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sélection V1.5 diversifiée :
    - au moins 3 stocks
    - max 2 positions par secteur dès la sélection
    - compléter avec meilleurs scores restants
    """
    ordered = sorted(scores, key=lambda x: x.get("defensive_score", 0.0), reverse=True)
    etfs, stocks = split_assets(ordered)

    selected: List[Dict[str, Any]] = []
    selected_tickers = set()
    sector_counts: Dict[str, int] = {}

    def can_add(asset: Dict[str, Any], max_per_sector: int = 2) -> bool:
        sector = str(asset.get("sector", "unknown"))
        return sector_counts.get(sector, 0) < max_per_sector

    def add_asset(asset: Dict[str, Any]) -> None:
        ticker = asset.get("ticker")
        sector = str(asset.get("sector", "unknown"))
        selected.append(deepcopy(asset))
        selected_tickers.add(ticker)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    # 1) garantir un minimum de stocks diversifiés
    for stock in stocks:
        ticker = stock.get("ticker")
        if ticker in selected_tickers:
            continue
        if can_add(stock, max_per_sector=2):
            add_asset(stock)
        if len([a for a in selected if str(a.get("type", "")).lower() == "stock"]) >= MIN_STOCK_COUNT:
            break

    # 2) compléter avec les meilleurs actifs restants en gardant la diversification
    for asset in ordered:
        ticker = asset.get("ticker")
        if ticker in selected_tickers:
            continue
        if not can_add(asset, max_per_sector=2):
            continue
        add_asset(asset)
        if len(selected) >= MAX_POSITIONS:
            break

    # 3) fallback si on n'a pas assez de positions : on relâche un peu la contrainte sectorielle
    if len(selected) < MIN_POSITIONS:
        for asset in ordered:
            ticker = asset.get("ticker")
            if ticker in selected_tickers:
                continue
            add_asset(asset)
            if len(selected) >= MIN_POSITIONS:
                break

    return selected[:MAX_POSITIONS]


def assign_raw_weights(selected: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    total_score = sum(float(a.get("defensive_score", 0.0)) for a in selected)

    weighted: List[Dict[str, Any]] = []
    for asset in selected:
        asset_copy = deepcopy(asset)
        raw_weight = (float(asset_copy.get("defensive_score", 0.0)) / total_score) if total_score > 0 else (1.0 / max(len(selected), 1))
        asset_copy["raw_weight"] = clamp_weight(raw_weight)
        asset_copy["weight"] = clamp_weight(min(raw_weight, MAX_WEIGHT_PER_ASSET))
        weighted.append(asset_copy)

    return weighted


def normalize_weights(assets: List[Dict[str, Any]]) -> None:
    total = sum(float(a.get("weight", 0.0)) for a in assets)
    if total <= 0:
        if not assets:
            return
        eq = 1.0 / len(assets)
        for a in assets:
            a["weight"] = clamp_weight(eq)
    else:
        for a in assets:
            a["weight"] = clamp_weight(float(a["weight"]) / total)

    diff = round(1.0 - sum(float(a["weight"]) for a in assets), 6)
    if assets and abs(diff) > 0:
        assets[0]["weight"] = clamp_weight(float(assets[0]["weight"]) + diff)


def get_sector_totals(assets: List[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for a in assets:
        sector = str(a.get("sector", "unknown"))
        out[sector] = round(out.get(sector, 0.0) + float(a.get("weight", 0.0)), 6)
    return out


def get_etf_total_weight(assets: List[Dict[str, Any]]) -> float:
    return round(sum(float(a.get("weight", 0.0)) for a in assets if str(a.get("type", "")).lower() == "etf"), 6)


def redistribute_to_stocks(assets: List[Dict[str, Any]], amount: float) -> None:
    stocks = [a for a in assets if str(a.get("type", "")).lower() == "stock"]
    if not stocks or amount <= 0:
        return

    total_score = sum(float(a.get("defensive_score", 0.0)) for a in stocks)
    if total_score <= 0:
        share = amount / len(stocks)
        for a in stocks:
            a["weight"] = clamp_weight(float(a["weight"]) + share)
        return

    for a in stocks:
        bonus = amount * (float(a.get("defensive_score", 0.0)) / total_score)
        a["weight"] = clamp_weight(float(a["weight"]) + bonus)


def enforce_etf_cap(assets: List[Dict[str, Any]]) -> None:
    etf_total = get_etf_total_weight(assets)
    if etf_total <= MAX_ETF_TOTAL_WEIGHT:
        return

    excess = etf_total - MAX_ETF_TOTAL_WEIGHT
    etfs = [a for a in assets if str(a.get("type", "")).lower() == "etf"]
    if etf_total > 0:
        for a in etfs:
            reduction = excess * (float(a["weight"]) / etf_total)
            a["weight"] = clamp_weight(float(a["weight"]) - reduction)

    redistribute_to_stocks(assets, excess)
    normalize_weights(assets)


def enforce_sector_caps(assets: List[Dict[str, Any]]) -> None:
    for _ in range(5):
        sector_totals = get_sector_totals(assets)
        over = {s: w for s, w in sector_totals.items() if w > MAX_SECTOR_WEIGHT + 1e-9}
        if not over:
            break

        for sector, total in over.items():
            excess = total - MAX_SECTOR_WEIGHT
            sector_assets = [a for a in assets if str(a.get("sector", "unknown")) == sector]
            non_sector_stocks = [
                a for a in assets
                if str(a.get("sector", "unknown")) != sector and str(a.get("type", "")).lower() == "stock"
            ]
            non_sector_other = [
                a for a in assets
                if str(a.get("sector", "unknown")) != sector and str(a.get("type", "")).lower() != "stock"
            ]

            if total > 0:
                for a in sector_assets:
                    reduction = excess * (float(a["weight"]) / total)
                    a["weight"] = clamp_weight(float(a["weight"]) - reduction)

            receivers = non_sector_stocks if non_sector_stocks else non_sector_other
            if receivers:
                total_score = sum(float(a.get("defensive_score", 0.0)) for a in receivers)
                if total_score > 0:
                    for a in receivers:
                        bonus = excess * (float(a.get("defensive_score", 0.0)) / total_score)
                        a["weight"] = clamp_weight(float(a["weight"]) + bonus)

        normalize_weights(assets)


def enforce_asset_caps(assets: List[Dict[str, Any]]) -> None:
    for _ in range(5):
        over_assets = [a for a in assets if float(a.get("weight", 0.0)) > MAX_WEIGHT_PER_ASSET + 1e-9]
        if not over_assets:
            break

        excess_pool = 0.0
        for a in over_assets:
            excess = float(a["weight"]) - MAX_WEIGHT_PER_ASSET
            a["weight"] = clamp_weight(MAX_WEIGHT_PER_ASSET)
            excess_pool += excess

        receivers = [a for a in assets if float(a.get("weight", 0.0)) < MAX_WEIGHT_PER_ASSET - 1e-9]
        if receivers and excess_pool > 0:
            total_score = sum(float(a.get("defensive_score", 0.0)) for a in receivers)
            if total_score > 0:
                for a in receivers:
                    bonus = excess_pool * (float(a.get("defensive_score", 0.0)) / total_score)
                    a["weight"] = clamp_weight(float(a["weight"]) + bonus)

        normalize_weights(assets)


def apply_constraints(selected: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not selected:
        return []

    assets = assign_raw_weights(selected)
    normalize_weights(assets)

    enforce_asset_caps(assets)
    enforce_etf_cap(assets)
    enforce_sector_caps(assets)
    enforce_asset_caps(assets)
    enforce_etf_cap(assets)
    normalize_weights(assets)

    return assets


def build_allocation_summary(assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    sector_weights = get_sector_totals(assets)
    etf_count = sum(1 for a in assets if str(a.get("type", "")).lower() == "etf")
    stock_count = sum(1 for a in assets if str(a.get("type", "")).lower() == "stock")
    etf_weight = get_etf_total_weight(assets)

    return {
        "sector_weights": sector_weights,
        "etf_count": etf_count,
        "stock_count": stock_count,
        "etf_weight": etf_weight,
        "max_sector_weight": round(max(sector_weights.values()) if sector_weights else 0.0, 6),
        "constraints_respected": {
            "etf_cap_ok": etf_weight <= MAX_ETF_TOTAL_WEIGHT + 1e-6,
            "stock_min_ok": stock_count >= MIN_STOCK_COUNT,
            "positions_range_ok": MIN_POSITIONS <= len(assets) <= MAX_POSITIONS,
            "max_sector_ok": (max(sector_weights.values()) if sector_weights else 0.0) <= MAX_SECTOR_WEIGHT + 1e-6,
            "max_asset_ok": all(float(a.get("weight", 0.0)) <= MAX_WEIGHT_PER_ASSET + 1e-6 for a in assets),
        }
    }


def build_defensive_allocation() -> Dict[str, Any]:
    payload = load_defensive_scores()
    scores = payload.get("scores", [])

    logger.info("Construction allocation défensive : %s actifs scorés en entrée.", len(scores))

    if not scores:
        return {
            "brick": BRICK_NAME,
            "env": payload.get("env", DEFAULT_ENV),
            "generated_at": utc_now_iso(),
            "target_exposure": 0.0,
            "target_positions": 0,
            "proposed_assets": [],
            "reason": "no_scored_assets",
            "summary": {},
        }

    selected = select_candidates(scores)
    allocated = apply_constraints(selected)

    proposed_assets = [
        {
            "ticker": asset.get("ticker"),
            "type": asset.get("type"),
            "sector": asset.get("sector"),
            "region": asset.get("region"),
            "weight": round(float(asset.get("weight", 0.0)), 6),
            "defensive_score": asset.get("defensive_score"),
            "quality_score": asset.get("quality_score"),
            "earnings_stability_score": asset.get("earnings_stability_score"),
            "low_vol_score": asset.get("low_vol_score"),
            "dividend_score": asset.get("dividend_score"),
            "liquidity_score": asset.get("liquidity_score"),
        }
        for asset in allocated
    ]

    summary = build_allocation_summary(allocated)

    return {
        "brick": BRICK_NAME,
        "env": payload.get("env", DEFAULT_ENV),
        "generated_at": utc_now_iso(),
        "target_exposure": get_target_exposure(),
        "target_positions": len(proposed_assets),
        "proposed_assets": proposed_assets,
        "reason": "v1_5_defensive_allocation",
        "constraints": {
            "min_positions": MIN_POSITIONS,
            "max_positions": MAX_POSITIONS,
            "min_stock_count": MIN_STOCK_COUNT,
            "max_weight_per_asset": MAX_WEIGHT_PER_ASSET,
            "max_sector_weight": MAX_SECTOR_WEIGHT,
            "max_etf_total_weight": MAX_ETF_TOTAL_WEIGHT,
        },
        "summary": summary,
    }


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage defensive_allocator ===")

    output = build_defensive_allocation()
    save_json_file(DEFENSIVE_ALLOCATIONS_PATH, output)

    logger.info(
        "Defensive allocator terminé | target_positions=%s | target_exposure=%s",
        output.get("target_positions", 0),
        output.get("target_exposure", 0.0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "target_positions": output.get("target_positions", 0),
        "target_exposure": output.get("target_exposure", 0.0),
        "output_file": str(DEFENSIVE_ALLOCATIONS_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final defensive_allocator : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans defensive_allocator : %s", e)
        raise
