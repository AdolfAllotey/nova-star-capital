from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
OUT = BASE / "global_preprod_weekly_review.json"

FILES = {
    "daily_report": BASE / "global_preprod_long_run_daily_report.json",
    "daily_check": BASE / "global_preprod_long_run_daily_check.json",
    "production_readiness": BASE / "global_preprod_production_readiness.json",
    "orchestration_audit": BASE / "global_orchestration_audit.json",
    "trend_monitor": BASE / "global_preprod_trend_monitor.json",
    "anomaly_detector": BASE / "global_preprod_anomaly_detector.json",
    "stress_tests": BASE / "global_preprod_stress_test_report.json",
}


def load(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


data = {k: load(v, {}) for k, v in FILES.items()}

daily = data["daily_report"]
check = data["daily_check"]
prod = data["production_readiness"]
audit = data["orchestration_audit"]
trend = data["trend_monitor"]
anomaly = data["anomaly_detector"]
stress = data["stress_tests"]

kpis = daily.get("kpis", {})
decision = daily.get("decision", {})

readiness_score = int(prod.get("readiness_score", 0))
progress_pct = int(prod.get("progress_pct", 0))

blocking_checks = int(kpis.get("orchestration_blocking_checks", 0))
warning_checks = int(kpis.get("orchestration_warning_checks", 0))
daily_failed = int(kpis.get("daily_checks_failed", 0))

anomaly_summary = anomaly.get("summary", {}) if isinstance(anomaly, dict) else {}
critical_anomalies = int(anomaly_summary.get("critical", 0))
warning_anomalies = int(anomaly_summary.get("warning", 0))

trend_status = trend.get("trend_status", "UNKNOWN")
stress_status = stress.get("status", "UNKNOWN")

global_health_score = max(
    0,
    min(
        100,
        readiness_score
        - (blocking_checks * 15)
        - (warning_checks * 3)
        - (critical_anomalies * 10)
        - (warning_anomalies * 2)
    )
)

if global_health_score >= 90:
    stability = "INSTITUTIONAL_GRADE"
elif global_health_score >= 75:
    stability = "STABLE"
elif global_health_score >= 60:
    stability = "DEGRADED"
else:
    stability = "CRITICAL"

if blocking_checks == 0 and critical_anomalies == 0:
    recommendation = "CONTINUE_PREPROD"
elif blocking_checks <= 1:
    recommendation = "CONTINUE_WITH_REVIEW"
else:
    recommendation = "PAUSE_AND_INVESTIGATE"

payload = {
    "status": "ok",
    "engine": "global_preprod_weekly_review_v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),

    "week": max(1, progress_pct // 12),

    "summary": {
        "global_health_score": global_health_score,
        "stability": stability,
        "trend_status": trend_status,
        "stress_status": stress_status,
        "blocking_checks": blocking_checks,
        "warning_checks": warning_checks,
        "critical_anomalies": critical_anomalies,
        "warning_anomalies": warning_anomalies,
    },

    "institutional_review": {
        "execution_integrity": "GOOD" if blocking_checks == 0 else "REVIEW",
        "governance_integrity": "GOOD" if blocking_checks == 0 else "WARNING",
        "risk_drift": "LOW" if warning_checks <= 2 else "MEDIUM",
        "anomaly_trend": "CLEAR" if critical_anomalies == 0 else "DEGRADING",
        "production_readiness_score": readiness_score,
    },

    "decision": {
        "recommendation": recommendation,
        "continue_preprod": recommendation != "PAUSE_AND_INVESTIGATE",
        "requires_manual_review": blocking_checks > 0 or critical_anomalies > 0,
    }
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
