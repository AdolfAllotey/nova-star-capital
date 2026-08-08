from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter

router = APIRouter(tags=["fills-board"])

DATA_DIR = Path("/opt/nsc/data/preprod")
OPEN_POSITIONS_PATH = DATA_DIR / "trading" / "open_positions.json"
EXIT_EVENTS_PATH = DATA_DIR / "trading" / "exit_events.json"


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v or default)
    except Exception:
        return default


def normalize_exit(row: Dict[str, Any]) -> Dict[str, Any]:
    pnl = num(row.get("pnl") or row.get("realized_pnl_eur") or row.get("pnl_eur") or 0)
    side = str(row.get("side") or "long").upper()
    exit_type = str(row.get("exit_type") or row.get("reason") or "EXIT")

    return {
        "ts": row.get("timestamp") or row.get("closed_at") or row.get("updated_at"),
        "engine": "crypto_position_manager",
        "plan_id": row.get("plan_id"),
        "order_id": row.get("order_id"),
        "policy": row.get("execution_mode") or "SIMULATED_ONLY",
        "symbol": row.get("symbol"),
        "side": "SELL" if side in ("LONG", "BUY") else side,
        "qty": row.get("size") or row.get("qty") or row.get("amount"),
        "fill_price": row.get("price") or row.get("exit_price"),
        "status": "REALIZED" if pnl != 0 else "CLOSED_ZERO",
        "pnl_eur": round(pnl, 4),
        "strategy": row.get("strategy"),
        "reason": row.get("reason") or exit_type,
        "event_type": exit_type,
    }


def normalize_open(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": row.get("opened_at") or row.get("timestamp") or row.get("updated_at"),
        "engine": "crypto_position_manager",
        "plan_id": row.get("plan_id"),
        "order_id": row.get("order_id"),
        "policy": row.get("execution_mode") or "SIMULATED_ONLY",
        "symbol": row.get("symbol"),
        "side": "BUY",
        "qty": row.get("size") or row.get("qty") or row.get("amount"),
        "fill_price": row.get("entry_price") or row.get("price") or row.get("price_ref"),
        "status": "OPEN",
        "pnl_eur": round(num(row.get("unrealized_pnl") or row.get("unrealized_pnl_eur") or 0), 4),
        "strategy": row.get("strategy"),
        "reason": "open_position_mark_to_market",
        "event_type": "open_position",
    }


@router.get("/api/fills-board")
def fills_board() -> Dict[str, Any]:
    exits = load_json(EXIT_EVENTS_PATH, [])
    opens = load_json(OPEN_POSITIONS_PATH, [])

    if not isinstance(exits, list):
        exits = []
    if not isinstance(opens, list):
        opens = []

    rows: List[Dict[str, Any]] = []
    rows.extend(normalize_exit(r) for r in exits if isinstance(r, dict))
    rows.extend(normalize_open(r) for r in opens if isinstance(r, dict))

    all_rows = sorted(rows, key=lambda r: str(r.get("ts") or ""), reverse=True)
    display_rows = all_rows[:150]

    buy_count = sum(1 for r in all_rows if str(r.get("side", "")).upper() == "BUY")
    sell_count = sum(1 for r in all_rows if str(r.get("side", "")).upper() == "SELL")
    realized_pnl = sum(num(r.get("pnl_eur")) for r in all_rows if str(r.get("status")) in ("REALIZED", "CLOSED_ZERO"))
    open_pnl = sum(num(r.get("pnl_eur")) for r in all_rows if str(r.get("status")) == "OPEN")

    return {
        "summary": {
            "fillsCount": len(all_rows),
            "buyCount": buy_count,
            "sellCount": sell_count,
            "realizedPnlEur": round(realized_pnl, 2),
            "openPnlEur": round(open_pnl, 2),
            "source": "crypto_exit_events_and_open_positions",
        },
        "rows": display_rows,
    }
