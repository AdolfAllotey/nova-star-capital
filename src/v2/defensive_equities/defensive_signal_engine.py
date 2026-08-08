"""
NSC - Defensive Equities - Defensive Signal Engine

V1.5 :
- charge defensive_allocations.json
- construit defensive_signal.json
- calcule une confidence simple
- standardise la sortie pour le futur portfolio_engine
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


DEFENSIVE_ALLOCATIONS_PATH = DATA_DIR / "defensive_allocations.json"
DEFENSIVE_SIGNAL_PATH = DATA_DIR / "defensive_signal.json"
PRICES_PATH = DATA_DIR / "prices.json"
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


def clamp_score(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return round(max(minimum, min(maximum, value)), 4)


def load_defensive_allocation() -> Dict[str, Any]:
    default_payload: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": DEFAULT_ENV,
        "generated_at": None,
        "target_exposure": 0.0,
        "target_positions": 0,
        "proposed_assets": [],
        "reason": "no_allocation",
        "summary": {},
    }

    payload = load_json_file(DEFENSIVE_ALLOCATIONS_PATH, default=default_payload)

    if not isinstance(payload, dict):
        logger.warning("Defensive allocation invalide : format non dict.")
        return default_payload

    if not isinstance(payload.get("proposed_assets", []), list):
        logger.warning("Defensive allocation invalide : 'proposed_assets' non list.")
        payload["proposed_assets"] = []

    return payload



def load_prices() -> Dict[str, float]:
    raw = load_json_file(PRICES_PATH, default={}) or {}
    if not isinstance(raw, dict):
        return {}

    prices: Dict[str, float] = {}
    for k, v in raw.items():
        try:
            px = float(v)
            if px > 0:
                prices[str(k).strip().upper()] = px
        except Exception:
            continue
    return prices


def filter_and_normalize_priced_assets(assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prices = load_prices()
    filtered = []

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        ticker = str(asset.get("ticker", "")).strip().upper()
        if not ticker:
            continue
        if ticker not in prices:
            logger.warning("Defensive asset skipped: missing price for %s", ticker)
            continue
        row = dict(asset)
        row["ticker"] = ticker
        filtered.append(row)

    total_weight = sum(float(a.get("weight", 0.0) or 0.0) for a in filtered)
    if total_weight <= 0:
        return []

    for asset in filtered:
        asset["weight"] = round(float(asset.get("weight", 0.0) or 0.0) / total_weight, 6)

    return filtered


def compute_signal_confidence(allocation: Dict[str, Any]) -> float:
    assets = filter_and_normalize_priced_assets(allocation.get("proposed_assets", []))
    summary = allocation.get("summary", {})
    constraints = summary.get("constraints_respected", {})

    if not assets:
        return 0.0

    avg_defensive_score = 0.0
    if assets:
        avg_defensive_score = sum(float(a.get("defensive_score", 0.0)) for a in assets) / len(assets)

    score_component = min(avg_defensive_score / 100.0, 1.0) * 0.70

    constraints_ok_count = sum(1 for v in constraints.values() if v is True) if isinstance(constraints, dict) else 0
    constraints_total = len(constraints) if isinstance(constraints, dict) and constraints else 1
    constraints_component = (constraints_ok_count / constraints_total) * 0.30

    confidence = score_component + constraints_component
    return clamp_score(confidence)


def compute_average_defensive_score(assets: List[Dict[str, Any]]) -> float:
    if not assets:
        return 0.0
    return round(sum(float(a.get("defensive_score", 0.0)) for a in assets) / len(assets), 2)


def estimate_portfolio_beta(assets: List[Dict[str, Any]]) -> float:
    """
    Approximation V1.5 basée sur les low_vol_scores pondérés.
    Plus tard : remplacer par un vrai calcul de bêta portefeuille.
    """
    if not assets:
        return 0.0

    beta_estimate = 0.0
    for asset in assets:
        weight = float(asset.get("weight", 0.0))
        low_vol_score = float(asset.get("low_vol_score", 0.0))

        # plus low_vol_score est élevé, plus le bêta estimé est faible
        asset_beta_proxy = max(0.45, 1.10 - (low_vol_score / 100.0) * 0.50)
        beta_estimate += weight * asset_beta_proxy

    return round(beta_estimate, 4)


def build_defensive_signal() -> Dict[str, Any]:
    allocation = load_defensive_allocation()
    assets = filter_and_normalize_priced_assets(allocation.get("proposed_assets", []))
    summary = allocation.get("summary", {})

    if not assets:
        return {
            "brick": BRICK_NAME,
            "env": allocation.get("env", DEFAULT_ENV),
            "generated_at": utc_now_iso(),
            "mode": "active",
            "target_exposure": 0.0,
            "confidence": 0.0,
            "proposed_assets": [],
            "reason": "no_eligible_allocation",
            "score_summary": {
                "average_defensive_score": 0.0,
                "selected_assets_count": 0,
                "portfolio_beta_estimate": 0.0,
                "constraints_respected": False,
            }
        }

    avg_defensive_score = compute_average_defensive_score(assets)
    portfolio_beta_estimate = estimate_portfolio_beta(assets)
    confidence = compute_signal_confidence(allocation)

    constraints_respected = all(
        summary.get("constraints_respected", {}).values()
    ) if isinstance(summary.get("constraints_respected", {}), dict) else False

    signal = {
        "brick": BRICK_NAME,
        "env": allocation.get("env", DEFAULT_ENV),
        "generated_at": utc_now_iso(),
        "mode": "active",
        "target_exposure": allocation.get("target_exposure", 0.0),
        "confidence": confidence,
        "proposed_assets": [
            {
                "ticker": asset.get("ticker"),
                "type": asset.get("type"),
                "sector": asset.get("sector"),
                "region": asset.get("region"),
                "weight": asset.get("weight"),
            }
            for asset in assets
        ],
        "reason": allocation.get("reason", "defensive_allocation_ready"),
        "score_summary": {
            "average_defensive_score": avg_defensive_score,
            "selected_assets_count": len(assets),
            "portfolio_beta_estimate": portfolio_beta_estimate,
            "constraints_respected": constraints_respected,
        }
    }

    return signal


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage defensive_signal_engine ===")

    signal = build_defensive_signal()
    save_json_file(DEFENSIVE_SIGNAL_PATH, signal)

    logger.info(
        "Defensive signal engine terminé | selected_assets_count=%s | confidence=%s",
        signal.get("score_summary", {}).get("selected_assets_count", 0),
        signal.get("confidence", 0.0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "selected_assets_count": signal.get("score_summary", {}).get("selected_assets_count", 0),
        "confidence": signal.get("confidence", 0.0),
        "output_file": str(DEFENSIVE_SIGNAL_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final defensive_signal_engine : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans defensive_signal_engine : %s", e)
        raise
