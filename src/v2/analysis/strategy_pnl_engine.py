"""
NSC Strategy PnL Engine
Builds a per-strategy PnL state for Executive / dashboards.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path("/opt/nsc/data/preprod/analysis")
TRADING_DIR = Path("/opt/nsc/data/preprod/trading")

OPEN_POSITIONS_PATH = TRADING_DIR / "open_positions.json"
TRADE_SIMULATION_PATH = TRADING_DIR / "trade_simulation.json"
EXIT_EVENTS_PATH = TRADING_DIR / "exit_events.json"
OUTPUT_PATH = DATA_DIR / "strategy_pnl_state.json"

DEFAULT_KEYS = [
    "crypto",
    "equities_offensive",
    "equities_defensive",
    "long_term",
    "options_us",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default=None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def safe_list(data):
    return data if isinstance(data, list) else []


def to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def pnl_value(row: dict) -> float:
    for key in ("pnl_eur", "pnl", "realized_pnl_eur", "realized_pnl"):
        if key in row and row.get(key) is not None:
            return to_float(row.get(key), 0.0)
    return 0.0


def map_strategy(row: dict) -> str:
    raw = str(row.get("strategy") or "").strip().lower()

    if raw in {"momentum", "market_momentum", "sniper", "whale", "crypto"}:
        return "crypto"
    if raw in {"equities_offensive", "offensive"}:
        return "equities_offensive"
    if raw in {"equities_defensive", "defensive"}:
        return "equities_defensive"
    if raw in {"long_term", "lt"}:
        return "long_term"
    if raw in {"options", "options_us"}:
        return "options_us"

    symbol = str(row.get("symbol") or "").lower()
    if symbol.endswith("usdt") or symbol.endswith("usd"):
        return "crypto"

    return "crypto"


def empty_row() -> dict:
    return {
        "realized_pnl_eur": 0.0,
        "unrealized_pnl_eur": 0.0,
        "total_pnl_eur": 0.0,
        "open_positions_count": 0,
        "open_notional_eur": 0.0,
        "simulated_trades_count": 0,
        "exit_events_count": 0,
    }


def build_strategy_pnl_state() -> dict:
    open_positions = safe_list(load_json(OPEN_POSITIONS_PATH, []))
    trade_simulation = safe_list(load_json(TRADE_SIMULATION_PATH, []))
    exit_events = safe_list(load_json(EXIT_EVENTS_PATH, []))

    rows = {key: empty_row() for key in DEFAULT_KEYS}

    for row in open_positions:
        key = map_strategy(row)
        rows.setdefault(key, empty_row())
        rows[key]["realized_pnl_eur"] += to_float(row.get("realized_pnl_eur", row.get("realized_pnl")), 0.0)
        rows[key]["unrealized_pnl_eur"] += to_float(row.get("unrealized_pnl_eur", row.get("unrealized_pnl")), 0.0)
        rows[key]["open_positions_count"] += 1
        rows[key]["open_notional_eur"] += to_float(row.get("notional_eur"), 0.0)

    for row in exit_events:
        key = map_strategy(row)
        rows.setdefault(key, empty_row())
        rows[key]["realized_pnl_eur"] += pnl_value(row)
        rows[key]["exit_events_count"] += 1

    for row in trade_simulation:
        key = map_strategy(row)
        rows.setdefault(key, empty_row())
        rows[key]["simulated_trades_count"] += 1

    for key in rows:
        rows[key]["realized_pnl_eur"] = round(rows[key]["realized_pnl_eur"], 2)
        rows[key]["unrealized_pnl_eur"] = round(rows[key]["unrealized_pnl_eur"], 2)
        rows[key]["total_pnl_eur"] = round(
            rows[key]["realized_pnl_eur"] + rows[key]["unrealized_pnl_eur"],
            2,
        )
        rows[key]["open_notional_eur"] = round(rows[key]["open_notional_eur"], 2)

    return {
        "env": "PREPROD",
        "generated_at": utc_now_iso(),
        "by_strategy": rows,
        "sources": {
            "open_positions": str(OPEN_POSITIONS_PATH),
            "trade_simulation": str(TRADE_SIMULATION_PATH),
            "exit_events": str(EXIT_EVENTS_PATH),
        },
    }


def save_strategy_pnl_state() -> dict:
    state = build_strategy_pnl_state()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    return state


if __name__ == "__main__":
    result = save_strategy_pnl_state()
    print(json.dumps(result, indent=2))
