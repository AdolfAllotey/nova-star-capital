import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/opt/nsc/app/src/v2/options_v2/data")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(name, default):
    path = BASE / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_snapshot(snapshot):
    path = BASE / "options_v2_daily_snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")


def append_snapshot_history(snapshot):
    path = BASE / "options_v2_snapshot_history.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def load_last_snapshot_from_history():
    path = BASE / "options_v2_snapshot_history.jsonl"
    if not path.exists():
        return None

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return None

    try:
        return json.loads(lines[-1])
    except Exception:
        return None


def safe_num(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def compute_delta(current_snapshot, previous_snapshot):
    if not previous_snapshot:
        return {
            "has_previous_snapshot": False,
            "unrealized_pnl_delta_eur": None,
            "realized_pnl_delta_eur": None,
            "open_positions_delta": None,
            "closed_positions_delta": None,
            "trades_total_delta": None,
        }

    cur_perf = current_snapshot.get("performance", {})
    prev_perf = previous_snapshot.get("performance", {})
    cur_port = current_snapshot.get("portfolio", {})
    prev_port = previous_snapshot.get("portfolio", {})

    return {
        "has_previous_snapshot": True,
        "unrealized_pnl_delta_eur": round(
            safe_num(cur_perf.get("aggregate_unrealized_pnl_eur", 0.0)) -
            safe_num(prev_perf.get("aggregate_unrealized_pnl_eur", 0.0)), 2
        ),
        "realized_pnl_delta_eur": round(
            safe_num(cur_perf.get("aggregate_realized_pnl_eur", 0.0)) -
            safe_num(prev_perf.get("aggregate_realized_pnl_eur", 0.0)), 2
        ),
        "open_positions_delta": int(cur_port.get("positions_open", 0)) - int(prev_port.get("positions_open", 0)),
        "closed_positions_delta": int(cur_port.get("positions_closed", 0)) - int(prev_port.get("positions_closed", 0)),
        "trades_total_delta": int(cur_perf.get("trades_total", 0)) - int(prev_perf.get("trades_total", 0)),
    }


def detect_anomalies(snapshot):
    perf = snapshot.get("performance", {})
    port = snapshot.get("portfolio", {})

    anomalies = []

    unrealized = safe_num(perf.get("aggregate_unrealized_pnl_eur", 0.0))
    realized = safe_num(perf.get("aggregate_realized_pnl_eur", 0.0))
    open_positions = int(port.get("positions_open", 0))
    closed_positions = int(port.get("positions_closed", 0))
    close_trades_total = int(perf.get("close_trades_total", 0))
    win_rate = safe_num(perf.get("win_rate_pct", 0.0))
    open_risk = safe_num(perf.get("aggregate_estimated_risk_open_eur", 0.0))

    if open_positions == 0 and open_risk > 0:
        anomalies.append("risk_without_open_positions")

    if closed_positions > 0 and close_trades_total == 0:
        anomalies.append("closed_positions_without_close_trades")

    if close_trades_total > 0 and (win_rate < 0 or win_rate > 100):
        anomalies.append("invalid_win_rate_range")

    if realized < -100000 or unrealized < -100000:
        anomalies.append("extreme_negative_pnl")

    return anomalies


def build_snapshot():
    status = load_json("options_v2_status.json", {})
    metrics = load_json("options_v2_metrics.json", {})
    positions = load_json("options_v2_positions.json", [])
    trades = load_json("options_v2_trades.json", [])
    decisions = load_json("options_v2_decisions.json", [])

    open_positions = [p for p in positions if p.get("status") == "OPEN"]
    closed_positions = [p for p in positions if p.get("status") == "CLOSED"]

    snapshot = {
        "ts": utc_now_iso(),
        "engine": "options_snapshot_v2",
        "status": status.get("status"),
        "mode": status.get("mode"),
        "portfolio": {
            "positions_open": len(open_positions),
            "positions_closed": len(closed_positions),
            "total_positions": len(positions)
        },
        "performance": metrics.get("summary", {}),
        "strategies": metrics.get("strategy_breakdown", {}),
        "decisions": decisions,
        "recent_trades": trades[-10:]
    }

    previous_snapshot = load_last_snapshot_from_history()
    snapshot["delta"] = compute_delta(snapshot, previous_snapshot)
    snapshot["anomalies"] = detect_anomalies(snapshot)

    return snapshot
