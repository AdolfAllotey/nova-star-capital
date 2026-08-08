#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

def get_last_price(symbol: str, prices_path: str = "/opt/nsc/data/preprod/equities_offensive/market/prices.json") -> Optional[float]:
    doc = load_json(Path(prices_path), default={}) or {}
    prices = (doc.get("prices") or {})
    px = prices.get(symbol)
    if px is None:
        return None
    try:
        px = float(px)
        return px if px > 0 else None
    except Exception:
        return None
