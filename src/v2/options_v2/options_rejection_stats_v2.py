import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/opt/nsc/app/src/v2/options_v2/data")
DECISIONS_FILE = BASE / "options_v2_decisions.json"
STATS_FILE = BASE / "options_v2_rejection_stats.json"


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


def pct(part, total):
    if not total:
        return 0.0
    return round((part / total) * 100.0, 2)


def update_rejection_stats():
    decisions = load_json(DECISIONS_FILE, [])
    stats = load_json(STATS_FILE, {
        "ts": None,
        "engine": "options_rejection_stats_v2",
        "totals": {
            "runs_count": 0,
            "decisions_total": 0,
            "approved_total": 0,
            "rejected_total": 0
        },
        "by_status": {},
        "by_reason": {},
        "ratios": {}
    })

    stats["ts"] = utc_now_iso()
    stats["engine"] = "options_rejection_stats_v2"
    stats["totals"]["runs_count"] += 1

    for decision in decisions:
        status = decision.get("status", "UNKNOWN")
        reason = decision.get("reason", "unknown_reason")

        stats["totals"]["decisions_total"] += 1

        if status == "APPROVED":
            stats["totals"]["approved_total"] += 1
        else:
            stats["totals"]["rejected_total"] += 1

        if status not in stats["by_status"]:
            stats["by_status"][status] = 0
        stats["by_status"][status] += 1

        if reason not in stats["by_reason"]:
            stats["by_reason"][reason] = 0
        stats["by_reason"][reason] += 1

    decisions_total = stats["totals"]["decisions_total"]
    approved_total = stats["totals"]["approved_total"]
    rejected_total = stats["totals"]["rejected_total"]

    rejected_cooldown = stats["by_status"].get("REJECTED_COOLDOWN", 0)
    rejected_risk = stats["by_status"].get("REJECTED_RISK", 0)
    rejected_signal = stats["by_status"].get("REJECTED_SIGNAL", 0)

    stats["ratios"] = {
        "approved_pct": pct(approved_total, decisions_total),
        "rejected_pct": pct(rejected_total, decisions_total),
        "rejected_cooldown_pct": pct(rejected_cooldown, decisions_total),
        "rejected_risk_pct": pct(rejected_risk, decisions_total),
        "rejected_signal_pct": pct(rejected_signal, decisions_total),
        "opportunity_conversion_pct": pct(approved_total, decisions_total)
    }

    save_json(STATS_FILE, stats)
    return stats
