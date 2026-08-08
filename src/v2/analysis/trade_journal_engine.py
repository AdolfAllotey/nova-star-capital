"""
NSC Trade Journal Engine
Builds a normalized trade journal for audit / learning / dashboarding.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

ANALYSIS_DIR = Path("/opt/nsc/data/preprod/analysis")
TRADING_DIR = Path("/opt/nsc/data/preprod/trading")

OPEN_POSITIONS_PATH = TRADING_DIR / "open_positions.json"
TRADE_SIMULATION_PATH = TRADING_DIR / "trade_simulation.json"
CAPITAL_ALLOCATOR_STATE_PATH = ANALYSIS_DIR / "capital_allocator_state.json"
OUTPUT_PATH = ANALYSIS_DIR / "trade_journal_state.json"

MAX_ROWS = 500


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


def normalize_row(row: dict, phase: str, regime: str, source: str) -> dict:
    """
    Normalize rows coming from heterogeneous trading artifacts.

    open_positions.json uses fields like:
      symbol, side, size, entry_price, realized_pnl, execution_mode

    trade_simulation.json uses fields like:
      token, action, amount, entry_price_eur, quantity_units, pnl_eur, status, risk_mode
    """

    symbol = (
        row.get("symbol")
        or row.get("ticker")
        or row.get("token")
        or row.get("asset")
        or "UNKNOWN"
    )

    action = row.get("action") or row.get("side") or "n/a"
    side = row.get("side") or row.get("action") or "unknown"

    strategy = (
        row.get("strategy")
        or row.get("strategy_name")
        or row.get("selection_source")
        or ("simulated_crypto" if source == "trade_simulation" else "unknown")
    )

    entry_price = (
        row.get("entry_price")
        if row.get("entry_price") is not None
        else row.get("entry_price_eur")
    )

    size = (
        row.get("size")
        if row.get("size") is not None
        else row.get("quantity_units")
    )

    remaining_size = (
        row.get("remaining_size")
        if row.get("remaining_size") is not None
        else row.get("quantity_units")
    )

    realized_pnl = (
        row.get("realized_pnl")
        if row.get("realized_pnl") is not None
        else row.get("pnl_eur")
    )

    execution_mode = (
        row.get("execution_mode")
        or row.get("status")
        or ("simulated" if source == "trade_simulation" else "n/a")
    )

    row_regime = row.get("regime") or row.get("risk_mode") or regime

    return {
        "ts": row.get("opened_at") or row.get("timestamp") or row.get("ts") or utc_now_iso(),
        "symbol": str(symbol).upper(),
        "strategy": strategy,
        "side": side,
        "entry_price": to_float(entry_price, 0.0),
        "size": to_float(size, 0.0),
        "remaining_size": to_float(remaining_size, 0.0),
        "notional_eur": to_float(row.get("notional_eur") or row.get("amount"), 0.0),
        "realized_pnl": to_float(realized_pnl, 0.0),
        "risk_flag": row.get("risk_flag") or row.get("risk_mode") or "n/a",
        "execution_mode": execution_mode,
        "action": action,
        "blocked_by": row.get("blocked_by") or [],
        "paper": bool(row.get("paper", source == "trade_simulation")),
        "phase": phase,
        "regime": row_regime,
        "source": source,
    }


def build_trade_journal_state() -> dict:
    open_positions = safe_list(load_json(OPEN_POSITIONS_PATH, []))
    trade_simulation = safe_list(load_json(TRADE_SIMULATION_PATH, []))
    allocator = load_json(CAPITAL_ALLOCATOR_STATE_PATH, {}) or {}

    phase = str(allocator.get("phase", "UNKNOWN") or "UNKNOWN")
    regime = str(allocator.get("regime", "UNKNOWN") or "UNKNOWN")

    rows = []

    for row in open_positions:
        rows.append(normalize_row(row, phase, regime, "open_positions"))

    for row in trade_simulation:
        rows.append(normalize_row(row, phase, regime, "trade_simulation"))

    rows.sort(key=lambda x: str(x.get("ts") or ""), reverse=True)
    rows = rows[:MAX_ROWS]

    summary = {
        "rows_count": len(rows),
        "open_positions_count": sum(1 for r in rows if r["source"] == "open_positions"),
        "trade_simulation_count": sum(1 for r in rows if r["source"] == "trade_simulation"),
        "total_realized_pnl_eur": round(sum(to_float(r.get("realized_pnl"), 0.0) for r in rows), 2),
    }

    return {
        "env": "PREPROD",
        "generated_at": utc_now_iso(),
        "summary": summary,
        "rows": rows,
        "sources": {
            "open_positions": str(OPEN_POSITIONS_PATH),
            "trade_simulation": str(TRADE_SIMULATION_PATH),
            "capital_allocator_state": str(CAPITAL_ALLOCATOR_STATE_PATH),
        },
    }


def save_trade_journal_state() -> dict:
    state = build_trade_journal_state()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    return state


if __name__ == "__main__":
    result = save_trade_journal_state()
    print(json.dumps(result, indent=2))
