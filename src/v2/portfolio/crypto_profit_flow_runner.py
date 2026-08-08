from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from src.v2.portfolio.profit_flow_runner import run as run_profit_flow

TRADE_SIM_PATH = Path("/opt/nsc/data/preprod/trading/trade_simulation.json")
OPEN_POS_PATH = Path("/opt/nsc/data/preprod/trading/open_positions.json")
CAPITAL_STATE_PATH = Path("/opt/nsc/data/preprod/analysis/capital_allocator_state.json")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def safe_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def sum_trade_values(rows):
    total_current = 0.0
    total_realized = 0.0

    if not isinstance(rows, list):
        return 0.0, 0.0

    for row in rows:
        if not isinstance(row, dict):
            continue
        total_current += safe_float(
            row.get("current_value_eur", row.get("entry_value_eur", row.get("notional_eur", row.get("amount", 0.0))))
        )
        total_realized += safe_float(row.get("pnl_eur", 0.0))

    return round(total_current, 2), round(total_realized, 2)


def main():
    trades = read_json(TRADE_SIM_PATH, []) or []
    open_positions = read_json(OPEN_POS_PATH, []) or []
    capital_state = read_json(CAPITAL_STATE_PATH, {}) or {}

    trades_capital, trades_profit = sum_trade_values(trades)
    open_capital, open_profit = sum_trade_values(open_positions)

    capital_eur = max(
        trades_capital,
        open_capital,
        safe_float((capital_state.get("totals") or {}).get("live_exposure_sum_eur", 0.0)),
        safe_float(capital_state.get("capital_observed_eur", 0.0)),
    )

    profit_eur = max(trades_profit, open_profit, 0.0)

    payload = {
        "status": "ok",
        "engine": "crypto_profit_flow_runner_v2",
        "trade_source": str(TRADE_SIM_PATH),
        "open_positions_source": str(OPEN_POS_PATH),
        "capital_state_source": str(CAPITAL_STATE_PATH),
        "profit_eur": round(profit_eur, 2),
        "capital_eur": round(capital_eur, 2),
        "timestamp": utc_now(),
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if profit_eur <= 0 or capital_eur <= 0:
        print(json.dumps({
            "status": "skipped",
            "reason": "profit_or_capital_not_positive",
            "profit_eur": round(profit_eur, 2),
            "capital_eur": round(capital_eur, 2),
        }, ensure_ascii=False, indent=2))
        return

    run_profit_flow(
        brick="crypto",
        profit_eur=profit_eur,
        capital_eur=capital_eur,
        source_pool="crypto_exchange_pool",
    )


if __name__ == "__main__":
    main()
