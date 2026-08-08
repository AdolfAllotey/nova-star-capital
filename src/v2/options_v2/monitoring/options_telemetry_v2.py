from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def build_options_metrics_v2(
    positions: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    positions = positions if isinstance(positions, list) else []
    trades = trades if isinstance(trades, list) else []
    candidates = candidates if isinstance(candidates, list) else []

    open_positions = [p for p in positions if p.get("status") == "OPEN"]
    closed_positions = [p for p in positions if p.get("status") == "CLOSED"]

    close_trades = [t for t in trades if t.get("action") == "CLOSE"]
    winning_close_trades = [t for t in close_trades if safe_float(t.get("pnl_eur", 0.0), 0.0) > 0]
    losing_close_trades = [t for t in close_trades if safe_float(t.get("pnl_eur", 0.0), 0.0) < 0]

    realized_pnl = round(sum(safe_float(t.get("pnl_eur", 0.0), 0.0) for t in close_trades), 2)
    unrealized_pnl = round(sum(safe_float(p.get("pnl_eur", 0.0), 0.0) for p in open_positions), 2)
    total_open_risk = round(sum(safe_float(p.get("estimated_risk_eur", 0.0), 0.0) for p in open_positions), 2)

    approved_candidates = [
        c for c in candidates
        if c.get("risk_validation", {}).get("approved", False)
    ]

    win_rate = 0.0
    if close_trades:
        win_rate = round((len(winning_close_trades) / len(close_trades)) * 100.0, 2)

    avg_realized_pnl = 0.0
    if close_trades:
        avg_realized_pnl = round(realized_pnl / len(close_trades), 2)

    avg_win_pnl = 0.0
    if winning_close_trades:
        avg_win_pnl = round(
            sum(safe_float(t.get("pnl_eur", 0.0), 0.0) for t in winning_close_trades) / len(winning_close_trades),
            2,
        )

    avg_loss_pnl = 0.0
    if losing_close_trades:
        avg_loss_pnl = round(
            sum(safe_float(t.get("pnl_eur", 0.0), 0.0) for t in losing_close_trades) / len(losing_close_trades),
            2,
        )

    avg_holding_period_days = 0.0
    if closed_positions:
        avg_holding_period_days = round(
            sum(safe_int(p.get("days_in_trade", 0), 0) for p in closed_positions) / len(closed_positions),
            2,
        )

    strategy_names = set()
    for p in positions:
        strategy_names.add(str(p.get("strategy", "unknown")))
    for t in trades:
        strategy_names.add(str(t.get("strategy", "unknown")))
    for c in candidates:
        strategy_names.add(str(c.get("strategy", "unknown")))

    strategy_breakdown: Dict[str, Dict[str, Any]] = {}
    for strategy in sorted(s for s in strategy_names if s and s != "unknown"):
        strategy_positions = [p for p in positions if p.get("strategy") == strategy]
        strategy_open_positions = [p for p in strategy_positions if p.get("status") == "OPEN"]
        strategy_closed_positions = [p for p in strategy_positions if p.get("status") == "CLOSED"]
        strategy_close_trades = [
            t for t in close_trades if t.get("strategy") == strategy
        ]

        strategy_realized = round(
            sum(safe_float(t.get("pnl_eur", 0.0), 0.0) for t in strategy_close_trades), 2
        )
        strategy_unrealized = round(
            sum(safe_float(p.get("pnl_eur", 0.0), 0.0) for p in strategy_open_positions), 2
        )
        strategy_risk = round(
            sum(safe_float(p.get("estimated_risk_eur", 0.0), 0.0) for p in strategy_open_positions), 2
        )

        strategy_win_rate = 0.0
        if strategy_close_trades:
            wins = [t for t in strategy_close_trades if safe_float(t.get("pnl_eur", 0.0), 0.0) > 0]
            strategy_win_rate = round((len(wins) / len(strategy_close_trades)) * 100.0, 2)

        strategy_breakdown[strategy] = {
            "count": len(strategy_positions),
            "open_count": len(strategy_open_positions),
            "closed_count": len(strategy_closed_positions),
            "close_trades_count": len(strategy_close_trades),
            "realized_pnl_eur": strategy_realized,
            "unrealized_pnl_eur": strategy_unrealized,
            "aggregate_estimated_risk_eur": strategy_risk,
            "win_rate_pct": strategy_win_rate,
        }

    return {
        "ts": utc_now_iso(),
        "engine": "options_telemetry_v2",
        "summary": {
            "candidates_total": len(candidates),
            "candidates_approved": len(approved_candidates),
            "positions_total": len(positions),
            "positions_open": len(open_positions),
            "positions_closed": len(closed_positions),
            "trades_total": len(trades),
            "close_trades_total": len(close_trades),
            "winning_close_trades": len(winning_close_trades),
            "losing_close_trades": len(losing_close_trades),
            "win_rate_pct": win_rate,
            "aggregate_realized_pnl_eur": realized_pnl,
            "aggregate_unrealized_pnl_eur": unrealized_pnl,
            "aggregate_estimated_risk_open_eur": total_open_risk,
            "avg_realized_pnl_per_close_trade_eur": avg_realized_pnl,
            "avg_win_pnl_eur": avg_win_pnl,
            "avg_loss_pnl_eur": avg_loss_pnl,
            "avg_holding_period_days_closed_positions": avg_holding_period_days,
        },
        "strategy_breakdown": strategy_breakdown,
    }
