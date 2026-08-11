from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
BASE.mkdir(parents=True, exist_ok=True)

LONG_RUN = BASE / "global_preprod_long_run_daily_report.json"
WEEKLY = BASE / "global_preprod_weekly_review.json"
OUT = BASE / "global_preprod_committee_review.json"


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_ts(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


long_run = load_json(LONG_RUN)
weekly = load_json(WEEKLY)

headline = long_run.get("headline", {})
kpis = long_run.get("kpis", {})
progress = long_run.get("progress", {})
session = long_run.get("session", {})
weekly_summary = weekly.get("summary", {})

now = datetime.now(timezone.utc)

target_days = int(
    progress.get("target_duration_days")
    or session.get("target_duration_days")
    or 30
)

current_day = int(progress.get("current_day") or 0)
progress_pct = float(progress.get("progress_pct") or 0.0)

started_at = parse_ts(progress.get("started_at"))
if started_at is None:
    started_at = now

end_at = started_at + timedelta(days=target_days)

health_score = int(weekly_summary.get("global_health_score", 100))
blocking = int(kpis.get("orchestration_blocking_checks", 0))
daily_failed = int(kpis.get("daily_checks_failed", 0))


def committee_status(score):
    if score >= 90:
        return "APPROVED"
    if score >= 75:
        return "WATCH"
    return "BLOCKED"


technical = committee_status(health_score)
risk = committee_status(health_score - blocking * 10)
governance = committee_status(health_score - daily_failed * 10)

if progress_pct >= 95 and blocking == 0 and daily_failed == 0:
    production = "ELIGIBLE"
elif progress_pct >= 50:
    production = "UNDER_REVIEW"
else:
    production = "OBSERVATION"

active_phase_obj = progress.get("active_phase") or {}
active_phase = (
    active_phase_obj.get("name")
    if isinstance(active_phase_obj, dict)
    else str(active_phase_obj or "RC2 Observation")
)

if target_days <= 30:
    milestones = [
        {"day": 0, "title": "Official RC2 launch"},
        {"day": 7, "title": "Week 1 stability review"},
        {"day": 14, "title": "Mid-cycle strategy & risk review"},
        {"day": 21, "title": "Performance & explainability review"},
        {"day": 30, "title": "RC2 final observation committee"},
    ]
else:
    milestones = [
        {"day": 7, "title": "Runtime stability validation"},
        {"day": 14, "title": "Governance consistency validation"},
        {"day": 21, "title": "Portfolio drift validation"},
        {"day": 30, "title": "Execution orchestration validation"},
        {"day": 45, "title": "Production simulation review"},
        {"day": 60, "title": "Final production committee"},
    ]

for m in milestones:
    m["status"] = "COMPLETED" if current_day >= m["day"] else "PENDING"

payload = {
    "engine": "global_preprod_committee_review_v2_rc2_clock_aware",
    "generated_at": now.isoformat(),
    "release": session.get("release"),
    "session_type": session.get("session_type"),
    "progress": {
        "elapsed_days": current_day,
        "remaining_days": max(0, target_days - current_day),
        "progress_pct": progress_pct,
        "eta": end_at.strftime("%d/%m/%Y"),
        "active_phase": active_phase,
        "target_duration_days": target_days,
    },
    "committees": {
        "technical_committee": technical,
        "risk_committee": risk,
        "governance_committee": governance,
        "production_committee": production,
    },
    "trajectory": {
        "health_score": health_score,
        "projection": "ON_TRACK" if health_score >= 90 else "WATCH",
        "confidence_trend": "IMPROVING" if health_score >= 90 else "STABLE",
    },
    "milestones": milestones,
}

OUT.write_text(
    json.dumps(payload, indent=2),
    encoding="utf-8",
)

print(json.dumps(payload, indent=2))
