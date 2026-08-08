import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/opt/nsc/app/src/v2/options_v2/data")

STATUS_FILE = BASE / "options_v2_status.json"
METRICS_FILE = BASE / "options_v2_metrics.json"
LEADERBOARD_FILE = BASE / "options_v2_leaderboard.json"
REJECTION_FILE = BASE / "options_v2_rejection_stats.json"
SNAPSHOT_FILE = BASE / "options_v2_daily_snapshot.json"
OUTPUT_FILE = BASE / "options_v2_daily_report.json"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def pick_first(items, default=None):
    if not items:
        return default
    return items[0]


def build_conclusion(status, summary, top_strategy, top_ticker, top_reason):
    positions_open = summary.get("positions_open", 0)
    realized = summary.get("aggregate_realized_pnl_eur", 0)
    unrealized = summary.get("aggregate_unrealized_pnl_eur", 0)
    win_rate = summary.get("win_rate_pct", 0)

    parts = []

    if status.get("status") == "ok":
        parts.append("Pipeline stable")
    else:
        parts.append("Pipeline à surveiller")

    if positions_open == 0:
        parts.append("aucune position ouverte")
    else:
        parts.append(f"{positions_open} position(s) ouverte(s)")

    parts.append(f"réalisé={realized} EUR")
    parts.append(f"non_réalisé={unrealized} EUR")
    parts.append(f"win_rate={win_rate}%")

    if top_strategy:
        parts.append(f"top_stratégie={top_strategy.get('name')}")
    if top_ticker:
        parts.append(f"top_ticker={top_ticker.get('name')}")
    if top_reason:
        parts.append(f"bloqueur_principal={top_reason.get('reason')}")

    return " | ".join(parts)


def generate_daily_report():
    status = load_json(STATUS_FILE, {})
    metrics = load_json(METRICS_FILE, {})
    leaderboard = load_json(LEADERBOARD_FILE, {})
    rejection = load_json(REJECTION_FILE, {})
    snapshot = load_json(SNAPSHOT_FILE, {})

    summary = metrics.get("summary", {})
    leaders = leaderboard.get("leaders", {})
    blockers = leaderboard.get("blockers", {})

    top_strategy = pick_first(leaders.get("top_strategy_by_realized_pnl", []), {})
    top_ticker = pick_first(leaders.get("top_ticker_by_realized_pnl", []), {})
    top_reason = pick_first(blockers.get("top_rejection_reasons", []), {})
    top_status = pick_first(blockers.get("top_rejection_statuses", []), {})

    report = {
        "ts": utc_now_iso(),
        "engine": "options_daily_report_v2",
        "status": {
            "pipeline_status": status.get("status"),
            "pipeline_version": status.get("version"),
            "mode": status.get("mode"),
            "message": status.get("message")
        },
        "portfolio": {
            "positions_open": summary.get("positions_open", 0),
            "positions_closed": summary.get("positions_closed", 0),
            "trades_total": summary.get("trades_total", 0),
            "close_trades_total": summary.get("close_trades_total", 0),
            "estimated_risk_open_eur": summary.get("aggregate_estimated_risk_open_eur", 0)
        },
        "performance": {
            "realized_pnl_eur": summary.get("aggregate_realized_pnl_eur", 0),
            "unrealized_pnl_eur": summary.get("aggregate_unrealized_pnl_eur", 0),
            "win_rate_pct": summary.get("win_rate_pct", 0),
            "avg_realized_pnl_per_close_trade_eur": summary.get("avg_realized_pnl_per_close_trade_eur", 0),
            "avg_holding_period_days_closed_positions": summary.get("avg_holding_period_days_closed_positions", 0)
        },
        "leaders": {
            "top_strategy_by_realized_pnl": top_strategy,
            "top_ticker_by_realized_pnl": top_ticker
        },
        "blockers": {
            "top_rejection_reason": top_reason,
            "top_rejection_status": top_status,
            "rejection_ratios": rejection.get("ratios", {})
        },
        "delta": snapshot.get("delta", {}),
        "anomalies": snapshot.get("anomalies", []),
        "conclusion": build_conclusion(
            status=status,
            summary=summary,
            top_strategy=top_strategy,
            top_ticker=top_ticker,
            top_reason=top_reason
        )
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
