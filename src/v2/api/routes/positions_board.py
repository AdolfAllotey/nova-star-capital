from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter

router = APIRouter(tags=["positions-board"])

POSITIONS_PATH = Path("data/equities_offensive/state/positions.json")
EXPOSURE_PATH = Path("data/equities_offensive/state/exposure_snapshot.json")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


@router.get("/api/positions-board")
def positions_board() -> Dict[str, Any]:
    positions_doc = load_json(POSITIONS_PATH, {}) or {}
    exposure_doc = load_json(EXPOSURE_PATH, {}) or {}

    raw_positions = positions_doc.get("positions", {})
    rows: List[Dict[str, Any]] = []

    if isinstance(raw_positions, dict):
        for symbol, pos in raw_positions.items():
            if not isinstance(pos, dict):
                continue
            qty = pos.get("qty", 0)
            side = "BUY" if float(qty or 0) >= 0 else "SELL"
            rows.append({
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "entry_price": pos.get("entry_price"),
                "notional_usd": pos.get("notional_usd"),
                "status": "OPEN",
            })

    summary = {
        "openPositions": len(rows),
        "grossExposureUsd": exposure_doc.get("gross_exposure_usd", 0) if isinstance(exposure_doc, dict) else 0,
        "netExposureUsd": exposure_doc.get("net_exposure_usd", 0) if isinstance(exposure_doc, dict) else 0,
    }

    return {
        "summary": summary,
        "rows": rows,
    }
