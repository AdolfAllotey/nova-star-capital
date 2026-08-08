"""
NSC PnL Engine
Builds a simple PnL state for Executive / dashboards.
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
OUTPUT_PATH = DATA_DIR / "pnl_state.json"


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


def build_pnl_state() -> dict:
    open_positions = safe_list(load_json(OPEN_POSITIONS_PATH, []))
    trade_simulation = safe_list(load_json(TRADE_SIMULATION_PATH, []))

    exit_events = safe_list(load_json(EXIT_EVENTS_PATH, []))

    # Source de vérité du réalisé : exit_events.json
    # Évite les doublons avec open_positions.realized_pnl.
    realized_pnl_eur = round(
        sum(to_float(row.get("pnl"), 0.0) for row in exit_events if isinstance(row, dict)),
        2,
    )

    active_open_positions = [
        row for row in open_positions
        if isinstance(row, dict)
        and row.get("closed") is not True
        and to_float(row.get("remaining_size", row.get("size", 0.0)), 0.0) > 0
    ]

    open_positions_notional_eur = round(
        sum(to_float(row.get("notional_eur"), 0.0) for row in active_open_positions),
        2
    )

    open_positions_count = len(active_open_positions)
    simulated_trades_count = len(trade_simulation)

    winners = 0
    losers = 0
    for row in trade_simulation:
        pnl = to_float(row.get("realized_pnl"), 0.0)
        if pnl > 0:
            winners += 1
        elif pnl < 0:
            losers += 1

    win_rate = round((winners / simulated_trades_count), 4) if simulated_trades_count > 0 else 0.0

    return {
        "env": "PREPROD",
        "generated_at": utc_now_iso(),
        "summary": {
            "realized_pnl_eur": realized_pnl_eur,
            "unrealized_pnl_eur": round(
                sum(to_float(row.get("unrealized_pnl"), 0.0) for row in active_open_positions),
                2,
            ),
            "total_pnl_eur": round(
                realized_pnl_eur
                + sum(to_float(row.get("unrealized_pnl"), 0.0) for row in active_open_positions),
                2,
            ),
            "open_positions_notional_eur": open_positions_notional_eur,
            "open_positions_count": open_positions_count,
            "simulated_trades_count": simulated_trades_count,
            "winning_trades": winners,
            "losing_trades": losers,
            "win_rate": win_rate
        },
        "sources": {
            "open_positions": str(OPEN_POSITIONS_PATH),
            "trade_simulation": str(TRADE_SIMULATION_PATH),
            "exit_events": str(EXIT_EVENTS_PATH)
        }
    }


def save_pnl_state() -> dict:
    state = build_pnl_state()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    return state


if __name__ == "__main__":
    result = save_pnl_state()
    print(json.dumps(result, indent=2))
