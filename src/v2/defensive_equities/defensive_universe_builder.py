"""
NSC - Defensive Equities - Universe Builder

Rôle :
- Charger la watchlist défensive
- Normaliser les entrées
- Dédupliquer les tickers
- Générer defensive_universe.json

Chemins attendus :
- Input  : src/v2/data/defensive/defensive_watchlist.json
- Output : src/v2/data/defensive/defensive_universe.json

Le script est volontairement robuste :
- fallback si certains utilitaires NSC ne sont pas encore branchés
- logger compatible avec une architecture V2-ready
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


WATCHLIST_PATH = DATA_DIR / "defensive_watchlist.json"
UNIVERSE_PATH = DATA_DIR / "defensive_universe.json"
LOG_PATH = LOG_DIR / "defensive_equities.log"

REQUIRED_FIELDS = {"ticker", "type", "sector", "region"}
ALLOWED_TYPES = {"stock", "etf"}


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


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


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


def normalize_ticker(ticker: str) -> str:
    return str(ticker).strip().upper()


def normalize_type(asset_type: str) -> str:
    return str(asset_type).strip().lower()


def normalize_text(value: Any) -> str:
    return str(value).strip().lower()


def load_defensive_watchlist() -> Dict[str, Any]:
    default_payload: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": DEFAULT_ENV,
        "generated_at": None,
        "watchlist_name": "NSC_defensive_v1",
        "assets": [],
    }

    payload = load_json_file(WATCHLIST_PATH, default=default_payload)

    if not isinstance(payload, dict):
        logger.warning("Watchlist invalide : format non dict. Fallback sur défaut.")
        return default_payload

    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        logger.warning("Watchlist invalide : 'assets' non list. Fallback sur liste vide.")
        payload["assets"] = []

    return payload


def validate_asset_entry(asset: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    if not isinstance(asset, dict):
        return ["asset_not_dict"]

    for field in REQUIRED_FIELDS:
        if field not in asset or asset[field] in (None, ""):
            errors.append(f"missing_{field}")

    asset_type = normalize_type(asset.get("type", ""))
    if asset_type and asset_type not in ALLOWED_TYPES:
        errors.append(f"invalid_type_{asset_type}")

    return errors


def normalize_asset_entry(asset: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {
        "ticker": normalize_ticker(asset.get("ticker", "")),
        "type": normalize_type(asset.get("type", "")),
        "sector": normalize_text(asset.get("sector", "")),
        "region": str(asset.get("region", "")).strip().upper(),
        "eligible": True,
        "exclusion_reason": None,
        "source": "defensive_watchlist",
        "metadata": {
            "raw_ticker": asset.get("ticker"),
            "raw_type": asset.get("type"),
            "raw_sector": asset.get("sector"),
            "raw_region": asset.get("region"),
        },
    }

    return normalized


def deduplicate_assets(assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []

    for asset in assets:
        ticker = asset.get("ticker")
        if not ticker:
            continue
        if ticker in seen:
            logger.warning("Ticker dupliqué ignoré : %s", ticker)
            continue
        seen.add(ticker)
        deduped.append(asset)

    return deduped


def build_defensive_universe() -> Dict[str, Any]:
    payload = load_defensive_watchlist()
    raw_assets = payload.get("assets", [])

    logger.info("Chargement watchlist défensive : %s actifs bruts.", len(raw_assets))

    normalized_assets: List[Dict[str, Any]] = []
    invalid_assets: List[Dict[str, Any]] = []

    for idx, asset in enumerate(raw_assets):
        errors = validate_asset_entry(asset)
        if errors:
            invalid_assets.append({
                "index": idx,
                "asset": asset,
                "errors": errors,
            })
            logger.warning("Actif invalide ignoré à l'index %s : %s", idx, errors)
            continue

        normalized_assets.append(normalize_asset_entry(asset))

    deduped_assets = deduplicate_assets(normalized_assets)

    universe: Dict[str, Any] = {
        "brick": BRICK_NAME,
        "env": payload.get("env", DEFAULT_ENV),
        "generated_at": utc_now_iso(),
        "watchlist_name": payload.get("watchlist_name", "NSC_defensive_v1"),
        "source_file": str(WATCHLIST_PATH),
        "universe_size": len(deduped_assets),
        "invalid_assets_count": len(invalid_assets),
        "invalid_assets": invalid_assets,
        "assets": deduped_assets,
    }

    return universe


def save_defensive_universe(universe: Dict[str, Any]) -> None:
    save_json_file(UNIVERSE_PATH, universe)
    logger.info("Universe sauvegardé : %s", UNIVERSE_PATH)


def run() -> Dict[str, Any]:
    ensure_directories()
    logger.info("=== Démarrage defensive_universe_builder ===")

    universe = build_defensive_universe()
    save_defensive_universe(universe)

    logger.info(
        "Universe construit avec succès | universe_size=%s | invalid_assets_count=%s",
        universe.get("universe_size", 0),
        universe.get("invalid_assets_count", 0),
    )

    return {
        "status": "ok",
        "brick": BRICK_NAME,
        "universe_size": universe.get("universe_size", 0),
        "invalid_assets_count": universe.get("invalid_assets_count", 0),
        "output_file": str(UNIVERSE_PATH),
    }


if __name__ == "__main__":
    try:
        result = run()
        logger.info("Résultat final : %s", result)
    except Exception as e:
        logger.exception("Erreur critique dans defensive_universe_builder : %s", e)
        raise
