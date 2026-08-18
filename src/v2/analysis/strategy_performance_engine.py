from pathlib import Path
from datetime import datetime, timezone
import json

DATA_DIR = Path("/opt/nsc/data/preprod")
OUT = DATA_DIR / "analysis" / "strategy_performance.json"

def load_json(path, default):
    try:
        if path.exists() and path.stat().st_size > 0:
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def ensure_strategy_index(open_positions):
    idx = {}
    for p in open_positions:
        sym = str(p.get("symbol", "")).lower()
        if sym:
            idx[sym] = str(p.get("strategy", "unknown")).lower()
    return idx

def add_trade(stats, strategy, pnl, source, symbol):
    strategy = strategy or "unknown"
    if strategy not in stats:
        stats[strategy] = {
            # Legacy V2 lifecycle accounting.
            # Kept unchanged for backward compatibility.
            "trades": 0,
            "wins": 0,
            "losses": 0,

            # V3 explicit event semantics.
            "lifecycle_events": 0,
            "economic_exit_events": 0,
            "zero_pnl_events": 0,
            "economic_wins": 0,
            "economic_losses": 0,

            "pnl_total": 0.0,
            "gross_win": 0.0,
            "gross_loss": 0.0,
            "symbols": {},
            "sources": {}
        }

    s = stats[strategy]

    # Legacy V2 lifecycle counter.
    s["trades"] += 1

    # V3 semantic accounting.
    s["lifecycle_events"] += 1

    s["pnl_total"] += pnl
    s["symbols"][symbol] = s["symbols"].get(symbol, 0) + 1
    s["sources"][source] = s["sources"].get(source, 0) + 1

    if pnl > 0:
        s["wins"] += 1
        s["economic_wins"] += 1
        s["economic_exit_events"] += 1
        s["gross_win"] += pnl

    elif pnl < 0:
        s["losses"] += 1
        s["economic_losses"] += 1
        s["economic_exit_events"] += 1
        s["gross_loss"] += abs(pnl)

    else:
        s["zero_pnl_events"] += 1

def main():
    open_positions = load_json(DATA_DIR / "trading" / "open_positions.json", [])
    exit_events = load_json(DATA_DIR / "trading" / "exit_events.json", [])

    if not isinstance(open_positions, list):
        open_positions = []
    if not isinstance(exit_events, list):
        exit_events = []

    strategy_by_symbol = ensure_strategy_index(open_positions)

    stats = {}

    # 1) PnL réalisé depuis sorties
    for e in exit_events:
        symbol = str(e.get("symbol", "")).lower()
        strategy = str(e.get("strategy") or strategy_by_symbol.get(symbol, "unknown")).lower()
        pnl = to_float(e.get("pnl", e.get("pnl_eur", 0.0)))
        add_trade(stats, strategy, pnl, "exit_events", symbol)

    # 2) PnL réalisé partiel sur positions ouvertes
    for p in open_positions:
        symbol = str(p.get("symbol", "")).lower()
        strategy = str(p.get("strategy", "unknown")).lower()
        pnl = to_float(p.get("realized_pnl", p.get("realized_pnl_eur", 0.0)))
        if pnl != 0:
            add_trade(stats, strategy, pnl, "open_positions_realized", symbol)

    for strategy, s in stats.items():
        trades = s["trades"]
        gross_loss = s["gross_loss"]
        s["pnl_total"] = round(s["pnl_total"], 4)
        s["gross_win"] = round(s["gross_win"], 4)
        s["gross_loss"] = round(s["gross_loss"], 4)
        # Legacy V2 metrics remain untouched.
        s["pnl_avg"] = round(
            s["pnl_total"] / trades,
            4
        ) if trades else 0.0

        s["winrate"] = round(
            s["wins"] / trades,
            4
        ) if trades else 0.0

        s["profit_factor"] = round(
            s["gross_win"] / gross_loss,
            4
        ) if gross_loss > 0 else None

        # V3 economic exit-event metrics.
        economic_events = s["economic_exit_events"]
        economic_wins = s["economic_wins"]
        economic_losses = s["economic_losses"]

        avg_win = (
            s["gross_win"] / economic_wins
            if economic_wins
            else None
        )

        avg_loss = (
            -(s["gross_loss"] / economic_losses)
            if economic_losses
            else None
        )

        s["economic_winrate"] = round(
            economic_wins / economic_events,
            4
        ) if economic_events else None

        s["economic_pnl_avg"] = round(
            s["pnl_total"] / economic_events,
            4
        ) if economic_events else None

        s["avg_win"] = (
            round(avg_win, 4)
            if avg_win is not None
            else None
        )

        s["avg_loss"] = (
            round(avg_loss, 4)
            if avg_loss is not None
            else None
        )

        s["payoff_ratio"] = (
            round(
                avg_win / abs(avg_loss),
                4,
            )
            if avg_win is not None
            and avg_loss is not None
            and avg_loss != 0
            else None
        )

        s["expectancy"] = s["economic_pnl_avg"]

        s["economic_profit_factor"] = (
            round(
                s["gross_win"] / gross_loss,
                4,
            )
            if gross_loss > 0
            else None
        )

        s["classified_economic_events"] = (
            economic_wins + economic_losses
        )

    payload = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "engine": "strategy_performance_engine_v3",
        "semantics_version": "v3_economic_exit_events",
        "mode": "lifecycle_and_economic_event_accounting",
        "metric_contract": {
            "trades": "legacy lifecycle event count; retained for backward compatibility",
            "winrate": "legacy wins divided by lifecycle events; retained for backward compatibility",
            "pnl_avg": "legacy pnl divided by lifecycle events; retained for backward compatibility",
            "economic_exit_events": "exit events with non-zero realized pnl",
            "zero_pnl_events": "exit events with zero realized pnl, including housekeeping lifecycle events",
            "economic_winrate": "economic wins divided by economic exit events",
            "economic_pnl_avg": "realized pnl divided by economic exit events",
            "expectancy": "mean realized pnl per economic exit event",
            "profit_factor": "gross wins divided by gross losses",
            "closed_trades": "not inferred by V3; partial exits may belong to the same position lifecycle"
        },
        "sources": {
            "exit_events": str(DATA_DIR / "trading" / "exit_events.json"),
            "open_positions": str(DATA_DIR / "trading" / "open_positions.json")
        },
        "by_strategy": stats
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
