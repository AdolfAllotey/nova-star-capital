import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/opt/nsc/app/src/v2/options_v2/data")
POSITIONS_FILE = BASE / "options_v2_positions.json"
TRADES_FILE = BASE / "options_v2_trades.json"
OUTPUT_FILE = BASE / "options_v2_advanced_stats.json"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_bucket(container, key):
    if key not in container:
        container[key] = {
            "positions_total": 0,
            "positions_open": 0,
            "positions_closed": 0,
            "open_trades": 0,
            "close_trades": 0,
            "winning_close_trades": 0,
            "losing_close_trades": 0,
            "realized_pnl_eur": 0.0,
            "unrealized_pnl_eur": 0.0,
            "estimated_risk_open_eur": 0.0,
            "win_rate_pct": 0.0
        }
    return container[key]


def finalize_bucket(bucket):
    close_trades = bucket.get("close_trades", 0)
    wins = bucket.get("winning_close_trades", 0)
    bucket["realized_pnl_eur"] = round(bucket.get("realized_pnl_eur", 0.0), 2)
    bucket["unrealized_pnl_eur"] = round(bucket.get("unrealized_pnl_eur", 0.0), 2)
    bucket["estimated_risk_open_eur"] = round(bucket.get("estimated_risk_open_eur", 0.0), 2)
    bucket["win_rate_pct"] = round((wins / close_trades) * 100.0, 2) if close_trades else 0.0


def build_advanced_stats():
    positions = load_json(POSITIONS_FILE, [])
    trades = load_json(TRADES_FILE, [])

    by_strategy = {}
    by_ticker = {}

    for p in positions:
        strategy = p.get("strategy", "UNKNOWN")
        ticker = p.get("ticker", "UNKNOWN")
        status = p.get("status", "UNKNOWN")
        pnl = float(p.get("pnl_eur", 0.0) or 0.0)
        risk = float(p.get("estimated_risk_eur", 0.0) or 0.0)

        s_bucket = ensure_bucket(by_strategy, strategy)
        t_bucket = ensure_bucket(by_ticker, ticker)

        for bucket in (s_bucket, t_bucket):
            bucket["positions_total"] += 1
            if status == "OPEN":
                bucket["positions_open"] += 1
                bucket["unrealized_pnl_eur"] += pnl
                bucket["estimated_risk_open_eur"] += risk
            elif status == "CLOSED":
                bucket["positions_closed"] += 1
                bucket["realized_pnl_eur"] += pnl

    for tr in trades:
        strategy = tr.get("strategy", "UNKNOWN")
        ticker = tr.get("ticker", "UNKNOWN")
        action = tr.get("action", "UNKNOWN")
        pnl = float(tr.get("pnl_eur", 0.0) or 0.0)

        s_bucket = ensure_bucket(by_strategy, strategy)
        t_bucket = ensure_bucket(by_ticker, ticker)

        for bucket in (s_bucket, t_bucket):
            if action == "OPEN":
                bucket["open_trades"] += 1
            elif action == "CLOSE":
                bucket["close_trades"] += 1
                if pnl > 0:
                    bucket["winning_close_trades"] += 1
                elif pnl < 0:
                    bucket["losing_close_trades"] += 1

    for bucket in by_strategy.values():
        finalize_bucket(bucket)

    for bucket in by_ticker.values():
        finalize_bucket(bucket)

    output = {
        "ts": utc_now_iso(),
        "engine": "options_advanced_stats_v2",
        "by_strategy": dict(sorted(by_strategy.items())),
        "by_ticker": dict(sorted(by_ticker.items()))
    }
    return output


def generate_advanced_stats():
    data = build_advanced_stats()
    save_json(OUTPUT_FILE, data)
    return data
