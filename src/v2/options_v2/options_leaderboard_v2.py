import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/opt/nsc/app/src/v2/options_v2/data")
ADVANCED_STATS_FILE = BASE / "options_v2_advanced_stats.json"
REJECTION_STATS_FILE = BASE / "options_v2_rejection_stats.json"
OUTPUT_FILE = BASE / "options_v2_leaderboard.json"


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


def sort_dict_section(section, key_name):
    items = []
    for name, stats in section.items():
        row = {"name": name}
        row.update(stats)
        items.append(row)
    return sorted(items, key=lambda x: x.get(key_name, 0), reverse=True)


def generate_leaderboard():
    advanced = load_json(ADVANCED_STATS_FILE, {})
    rejection = load_json(REJECTION_STATS_FILE, {})

    by_strategy = advanced.get("by_strategy", {})
    by_ticker = advanced.get("by_ticker", {})
    by_reason = rejection.get("by_reason", {})
    by_status = rejection.get("by_status", {})

    strategy_by_realized = sort_dict_section(by_strategy, "realized_pnl_eur")
    strategy_by_winrate = sort_dict_section(by_strategy, "win_rate_pct")
    ticker_by_realized = sort_dict_section(by_ticker, "realized_pnl_eur")
    ticker_by_winrate = sort_dict_section(by_ticker, "win_rate_pct")

    blockers_by_reason = sorted(
        [{"reason": k, "count": v} for k, v in by_reason.items()],
        key=lambda x: x["count"],
        reverse=True
    )
    blockers_by_status = sorted(
        [{"status": k, "count": v} for k, v in by_status.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    data = {
        "ts": utc_now_iso(),
        "engine": "options_leaderboard_v2",
        "leaders": {
            "top_strategy_by_realized_pnl": strategy_by_realized[:5],
            "top_strategy_by_win_rate": strategy_by_winrate[:5],
            "top_ticker_by_realized_pnl": ticker_by_realized[:10],
            "top_ticker_by_win_rate": ticker_by_winrate[:10]
        },
        "blockers": {
            "top_rejection_reasons": blockers_by_reason[:10],
            "top_rejection_statuses": blockers_by_status[:10]
        }
    }

    save_json(OUTPUT_FILE, data)
    return data
