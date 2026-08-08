from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

BRICK_NAME = "defensive_equities"
DEFAULT_ENV = os.getenv("NSC_ENV", "PREPROD")

BASE_DIR = Path(__file__).resolve().parents[3]
ROOT_DATA_DIR = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))
DATA_DIR = ROOT_DATA_DIR / "defensive"
LOG_DIR = ROOT_DATA_DIR / "logs"
LOG_PATH = LOG_DIR / "defensive_equities.log"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str = BRICK_NAME) -> logging.Logger:
    ensure_directories()

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


def load_json_file(path: Path, default: Optional[Any] = None, logger: Optional[logging.Logger] = None) -> Any:
    if not path.exists():
        return deepcopy(default)

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        if logger:
            logger.error("Erreur lecture JSON %s : %s", path, e)
        return deepcopy(default)


def save_json_file(path: Path, data: Any, logger: Optional[logging.Logger] = None) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        if logger:
            logger.error("Erreur sauvegarde JSON %s : %s", path, e)
        raise


def clamp_score(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, value)), 2)


def clamp_weight(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return round(max(minimum, min(maximum, value)), 6)


DEFENSIVE_UNIVERSE_PATH = DATA_DIR / "defensive_universe.json"


def load_defensive_universe(
    default: Optional[list[str]] = None,
    logger: Optional[logging.Logger] = None,
) -> list[str]:
    """
    Charge l'univers défensif depuis la source unique de préproduction.
    Fallback volontairement conservateur si le fichier est absent ou invalide.
    """
    fallback = default or [
        "PG", "KO", "PEP", "JNJ", "WMT", "CL", "MRK", "DUK", "SO",
        "AI", "NESN", "UL", "ROG", "VIG", "XLP", "VDC", "USMV", "XLV",
        "ASML", "COST", "UNH", "LLY"
    ]

    data = load_json_file(DEFENSIVE_UNIVERSE_PATH, default={}, logger=logger)

    tickers = data.get("tickers") if isinstance(data, dict) else None

    if not isinstance(tickers, list) or not tickers:
        if logger:
            logger.warning(
                "Univers défensif absent ou invalide, fallback utilisé: %s",
                DEFENSIVE_UNIVERSE_PATH,
            )
        return fallback

    cleaned = []
    for ticker in tickers:
        if isinstance(ticker, str) and ticker.strip():
            cleaned.append(ticker.strip().upper())

    if not cleaned:
        if logger:
            logger.warning("Univers défensif vide après nettoyage, fallback utilisé.")
        return fallback

    return sorted(set(cleaned))
