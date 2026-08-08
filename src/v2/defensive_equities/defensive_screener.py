"""
NSC - Defensive Equities - Screener

Rôle :
- Charger defensive_universe.json
- Appliquer un screener V1.5 simple et robuste
- Produire defensive_screened_universe.json

En V1.5, le screener reste volontairement simple :
- validation structurelle des champs
- filtrage par type autorisé
- filtrage par secteur défensif autorisé
- filtrage par région autorisée

Les filtres market cap / liquidité / bêta pourront être ajoutés ensuite
quand la brique data fundamentals sera branchée.
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


UNIVERSE_PATH = DATA_DIR / "defensive_universe.json"
SCREENED_UNIVERSE_PATH = DATA_DIR / "defensive_screened_universe.json"
LOG_PATH = LOG_DIR / "defensive_equities.log"

ALLOWED_TYPES = {"stock", "etf"}
ALLOWED_REGIONS = {"US", "EU", "CA"}
ALLOWED_SECTORS = {
    "consumer_staples",
    "consumer_defensive",
    "healthcare",
    "utilities",
    "infrastructure",
    "minimum_volatility",
    "dividend_growth",
    "luxury",
    "industrial_gas",
    "technology",
}


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


def load_defensive_universe() -> Dict[str, Any]:
    default_payload: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": DEFAULT_ENV,
        "generated_at": None,
        "watchlist_name": "NSC_defensive_v1",
        "source_file": str(UNIVERSE_PATH),
        "universe_size": 0,
        "invalid_assets_count": 0,
        "invalid_assets": [],
        "assets": [],
    }

    payload = load_json_file(UNIVERSE_PATH, default=default_payload)

    if not isinstance(payload, dict):
        logger.warning("Universe invalide : format non dict. Fallback sur défaut.")
        return default_payload

    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        logger.warning("Universe invalide : 'assets' non list. Fallback sur liste vide.")
        payload["assets"] = []

    return payload


def screen_asset(asset: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(asset.get("ticker", "")).strip().upper()
    asset_type = str(asset.get("type", "")).strip().lower()
    sector = str(asset.get("sector", "")).strip().lower()
    region = str(asset.get("region", "")).strip().upper()

    screen_checks = {
        "ticker_ok": bool(ticker),
        "type_ok": asset_type in ALLOWED_TYPES,
        "sector_ok": sector in ALLOWED_SECTORS,
        "region_ok": region in ALLOWED_REGIONS,
        "eligible_flag_ok": bool(asset.get("eligible", True)),
    }

    failed_reasons = [
        key.replace("_ok", "")
        for key, value in screen_checks.items()
        if not value
    ]

    screen_passed = all(screen_checks.values())

    screened_asset = deepcopy(asset)
    screened_asset["screen_passed"] = screen_passed
    screened_asset["screen_checks"] = screen_checks
    screened_asset["screen_failed_reasons"] = failed_reasons

    if not screen_passed:
        screened_asset["eligible"] = False
        screened_asset["exclusion_reason"] = ",".join(failed_reasons) if failed_reasons else "screen_failed"

    return screened_asset


def screen_defensive_universe() -> Dict[str, Any]:
    payload = load_defensive_universe()
    raw_assets = payload.get("assets", [])

    logger.info("Screening universe défensif : %s actifs entrants.", len(raw_assets))

    screened_assets = [screen_asset(asset) for asset in raw_assets]
    passed_assets = [asset for asset in screened_assets if asset.get("screen_passed")]

    result: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": payload.get("env", DEFAULT_ENV),
        "generated_at": utc_now_iso(),
        "watchlist_name": payload.get("watchlist_name", "NSC_defensive_v1"),
        "source_file": str(UNIVERSE_PATH),
        "input_universe_size": len(raw_assets),
        "screened_universe_size": len(passed_assets),
        "excluded_assets_count": len(raw_assets) - len(passed_assets),
        "assets": screened_assets,
    }

    return result


def save_screened_universe(screened: Dict[str, Any]) -> None:
    save_json_file(SCREENED_UNIVERSE_PATH, screened)
    logger.info("Screened universe sauvegardé : %s", SCREENED_UNIVERSE_PATH)


def run() -> Dict[str, Any]:
    logger.info("=== Démarrage defensive_screener ===")

    screened = screen_defensive_universe()
    save_screened_universe(screened)

    logger.info(
        "Screener terminé | input_universe_size=%s | screened_universe_size=%s | excluded_assets_count=%s",
        screened.get("input_universe_size", 0),
        screened.get("screened_universe_size", 0),
        screened.get("excluded_assets_count", 0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "input_universe_size": screened.get("input_universe_size", 0),
        "screened_universe_size": screened.get("screened_universe_size", 0),
        "excluded_assets_count": screened.get("excluded_assets_count", 0),
        "output_file": str(SCREENED_UNIVERSE_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final screener : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans defensive_screener : %s", e)
        raise
