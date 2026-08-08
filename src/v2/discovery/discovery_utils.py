from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List


def get_data_dir() -> Path:
    return Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_symbol(raw: str) -> str:
    s = str(raw or "").upper().strip()
    if s.endswith("USDT"):
        s = s[:-4]
    return s


def normalize_mover(row: Dict[str, Any], source_hint: str) -> Dict[str, Any] | None:
    symbol = normalize_symbol(row.get("symbol") or row.get("token") or row.get("id"))
    if not symbol:
        return None

    pair = row.get("pair") or f"{symbol}USDT"

    try:
        chg_24h = float(row.get("chg_24h") or row.get("change_24h") or row.get("price_change_percentage_24h") or 0.0)
    except Exception:
        chg_24h = 0.0

    try:
        price = float(row.get("price")) if row.get("price") is not None else None
    except Exception:
        price = None

    return {
        "symbol": symbol,
        "pair": pair,
        "source": row.get("source") or source_hint,
        "exchange": row.get("preferred_exchange") or row.get("exchange") or row.get("source") or source_hint,
        "price": price,
        "chg_24h": chg_24h,
        "category": "top_gainer" if chg_24h > 0 else "top_loser",
        "tradable": bool(row.get("tradable", True)),
        "observation_only": bool(row.get("observation_only", False)),
        "raw": row,
    }
