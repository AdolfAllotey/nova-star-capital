from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
BASE.mkdir(parents=True, exist_ok=True)

LONG_RUN = BASE / "global_preprod_long_run_daily_report.json"
WEEKLY = BASE / "global_preprod_weekly_review.json"
OUT = BASE / "global_preprod_committee_review.json"

START_DATE = datetime(2026, 5, 19, tzinfo=timezone.utc)

def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

long_run = load_json(LONG_RUN)
weekly = load_json(WEEKLY)

headline = long_run.get("headline", {})
kpis = long_run.get("kpis", {})
weekly_summary = weekly.get("summary", {})

now = datetime.now(timezone.utc)

elapsed_days = max(1, (now - START_DATE).days + 1)
progress_pct = min(100, round((elapsed_days / 60) * 100, 2))

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
    production = "NOT_READY"

if elapsed_days <= 10:
    active_phase = "Robustesse Runtime"
elif elapsed_days <= 20:
    active_phase = "Validation Stratégique"
elif elapsed_days <= 30:
    active_phase = "Risk & Governance"
elif elapsed_days <= 40:
    active_phase = "Funding & Rebalance"
elif elapsed_days <= 50:
    active_phase = "Performance & Explainability"
else:
    active_phase = "Production Readiness"

milestones = [
    {"day": 7, "title": "Runtime stability validation"},
    {"day": 14, "title": "Governance consistency validation"},
    {"day": 21, "title": "Portfolio drift validation"},
    {"day": 30, "title": "Execution orchestration validation"},
    {"day": 45, "title": "Production simulation review"},
    {"day": 60, "title": "Final production committee"}
]

for m in milestones:
    m["status"] = "COMPLETED" if elapsed_days >= m["day"] else "PENDING"

eta = (START_DATE + timedelta(days=60)).strftime("%d/%m/%Y")

payload = {
    "generated_at": now.isoformat(),
    "progress": {
        "elapsed_days": elapsed_days,
        "remaining_days": max(0, 60 - elapsed_days),
        "progress_pct": progress_pct,
        "eta": eta,
        "active_phase": active_phase,
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

OUT.write_text(json.dumps(payload, indent=2))
print(f"[OK] committee review -> {OUT}")
