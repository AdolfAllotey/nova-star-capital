from datetime import datetime, timezone
from typing import List, Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_options_metrics(
    positions: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    open_positions = [p for p in positions if p.get("status") == "OPEN"]
    closed_positions = [p for p in positions if p.get("status") == "CLOSED"]

    close_trades = [t for t in trades if t.get("action") == "CLOSE"]
    wins = [t for t in close_trades if float(t.get("pnl_eur", 0.0)) > 0]
    losses = [t for t in close_trades if float(t.get("pnl_eur", 0.0)) <= 0]

    strategy_breakdown: Dict[str, Dict[str, Any]] = {}

    for p in positions:
        strategy = p.get("strategy", "unknown")
        if strategy not in strategy_breakdown:
            strategy_breakdown[strategy] = {
                "count": 0,
                "open_count": 0,
                "closed_count": 0,
                "aggregate_pnl_eur": 0.0,
                "aggregate_estimated_risk_eur": 0.0,
            }

        strategy_breakdown[strategy]["count"] += 1

        if p.get("status") == "OPEN":
            strategy_breakdown[strategy]["open_count"] += 1

        if p.get("status") == "CLOSED":
            strategy_breakdown[strategy]["closed_count"] += 1

        strategy_breakdown[strategy]["aggregate_pnl_eur"] += float(p.get("pnl_eur", 0.0))
        strategy_breakdown[strategy]["aggregate_estimated_risk_eur"] += float(p.get("estimated_risk_eur", 0.0))

    metrics = {
        "ts": utc_now_iso(),
        "engine": "options_telemetry_v1",
        "summary": {
            "candidates_total": len(candidates),
            "candidates_approved": len([
                c for c in candidates
                if c.get("risk_validation", {}).get("approved", False)
            ]),
            "positions_total": len(positions),
            "positions_open": len(open_positions),
            "positions_closed": len(closed_positions),
            "trades_total": len(trades),
            "close_trades_total": len(close_trades),
            "win_rate": round((len(wins) / len(close_trades)) * 100, 2) if close_trades else 0.0,
            "aggregate_realized_pnl_eur": round(
                sum(float(t.get("pnl_eur", 0.0)) for t in close_trades),
                2
            ),
            "aggregate_unrealized_pnl_eur": round(
                sum(float(p.get("pnl_eur", 0.0)) for p in open_positions),
                2
            ),
            "aggregate_estimated_risk_open_eur": round(
                sum(float(p.get("estimated_risk_eur", 0.0)) for p in open_positions),
                2
            ),
        },
        "strategy_breakdown": strategy_breakdown,
    }

    return metrics
