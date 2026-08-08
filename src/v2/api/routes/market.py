from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
from pathlib import Path
import json
import datetime as dt

from src.v2.utils.file_utils import get_data_dir

router = APIRouter(prefix="/market", tags=["market"])

DATA_ROOT = Path(get_data_dir())
SPOT_PRICES_PATH = DATA_ROOT / "market" / "crypto_spot_prices.json"


def _iso_mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return dt.datetime.utcfromtimestamp(path.stat().st_mtime).replace(microsecond=0).isoformat() + "Z"


def _symbol_from_key(k: str) -> str:
    s = str(k).upper()
    if s.endswith("USDT"):
        s = s[:-4]
    return s


@router.get("/top-movers")
def get_top_movers() -> Dict[str, Any]:
    path = SPOT_PRICES_PATH

    if not path.exists():
        return {
            "updated_at": None,
            "items": [],
            "message": f"Fichier introuvable: {path}",
        }

    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lecture KO: {e}")

    if not isinstance(payload, dict):
        return {
            "updated_at": _iso_mtime(path),
            "items": [],
            "message": f"Format invalide dans {path}",
        }

    items: List[Dict[str, Any]] = []
    for key, value in payload.items():
        try:
            price = float(value)
        except Exception:
            continue

        symbol = _symbol_from_key(key)
        items.append({
            "symbol": symbol,
            "name": symbol,
            "price": price,
            "change_24h": None,
            "source": "crypto_spot_prices.json",
        })

    items.sort(key=lambda x: x["symbol"])

    return {
        "updated_at": _iso_mtime(path),
        "items": items,
        "message": None if items else "Aucune donnée exploitable.",
    }
