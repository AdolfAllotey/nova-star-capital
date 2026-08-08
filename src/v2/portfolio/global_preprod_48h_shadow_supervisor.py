from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")

SESSION = BASE / "global_preprod_48h_shadow_session.json"
HISTORY = BASE / "global_preprod_history_summary.json"
TREND = BASE / "global_preprod_trend_monitor.json"
ANOMALY = BASE / "global_preprod_anomaly_detector.json"
READINESS = BASE / "global_preprod_long_run_readiness.json"
STRESS = BASE / "global_preprod_stress_test_report.json"
INSTITUTIONAL = BASE / "institutional_supervision_summary.json"

OUT = BASE / "global_preprod_48h_shadow_supervisor.json"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_load_error": str(e)}


session = load(SESSION)
history = load(HISTORY)
trend = load(TREND)
anomaly = load(ANOMALY)
readiness = load(READINESS)
stress = load(STRESS)
institutional = load(INSTITUTIONAL)

preprod_safe_nominal = institutional.get("preprod_safe_nominal") is True
institutional_ready = institutional.get("institutional_layer_ready") is True

now_dt = datetime.now(timezone.utc)

started_at = session.get("started_at")
try:
    started_dt = datetime.fromisoformat(started_at) if started_at else now_dt
except Exception:
    started_dt = now_dt

elapsed_hours = round((now_dt - started_dt).total_seconds() / 3600, 2)
target_hours = float(session.get("target_duration_hours") or 48)
progress_pct = round(min(100.0, (elapsed_hours / target_hours) * 100), 2) if target_hours else 0.0

history_summary = history.get("summary") or {}
trend_metrics = trend.get("metrics") or {}
anomaly_summary = anomaly.get("summary") or {}
readiness_summary = readiness.get("summary") or {}
stress_summary = stress.get("summary") or {}

checks = []

def add_check(name: str, passed: bool, details: dict):
    checks.append({
        "name": name,
        "passed": bool(passed),
        "details": details,
    })


add_check(
    "session_active_or_long_run_superseded",
    session.get("status") == "active" or preprod_safe_nominal,
    {
        "status": session.get("status"),
        "mode": session.get("mode"),
        "preprod_safe_nominal": preprod_safe_nominal,
        "rule": "48h shadow is superseded by active 60D PREPROD long run when PREPROD SAFE nominal is ready.",
    },
)

trend_window = trend.get("window") or {}
window_failed_runs = int(trend_metrics.get("failed_runs") or 0)
historical_failed_runs = int(history_summary.get("failed_runs") or 0)

add_check(
    "no_failed_runs_during_shadow",
    window_failed_runs == 0,
    {
        "window_failed_runs": window_failed_runs,
        "window_total_runs": trend_metrics.get("total_runs"),
        "historical_failed_runs": historical_failed_runs,
        "window": trend_window,
        "rule": "48h shadow health is judged on the latest monitoring window; historical failures remain informational.",
    },
)

add_check(
    "trend_healthy",
    trend.get("trend_status") == "HEALTHY",
    {"trend_status": trend.get("trend_status"), "alerts": trend.get("alerts")},
)

add_check(
    "anomaly_clear",
    anomaly.get("anomaly_status") == "CLEAR",
    {"anomaly_status": anomaly.get("anomaly_status"), "summary": anomaly_summary},
)

add_check(
    "readiness_ready",
    readiness.get("readiness_status") == "READY" or institutional_ready,
    {
        "readiness_status": readiness.get("readiness_status"),
        "institutional_layer_ready": institutional_ready,
        "summary": readiness_summary,
    },
)

add_check(
    "stress_tests_green",
    stress.get("status") == "ok" and int(stress_summary.get("failed") or 0) == 0,
    {"stress_status": stress.get("status"), "summary": stress_summary},
)

failed = [c for c in checks if not c["passed"]]

shadow_status = "RUNNING"
if preprod_safe_nominal and institutional_ready and not failed:
    shadow_status = "SUPERSEDED_BY_60D_LONG_RUN"
elif failed:
    shadow_status = "ATTENTION"
elif progress_pct >= 100:
    shadow_status = "COMPLETED_READY_FOR_REVIEW"

payload = {
    "status": "ok",
    "engine": "global_preprod_48h_shadow_supervisor_v1_1_window_aware",
    "generated_at": now_dt.isoformat(),
    "shadow_status": shadow_status,
    "progress": {
        "started_at": session.get("started_at"),
        "elapsed_hours": elapsed_hours,
        "target_hours": target_hours,
        "progress_pct": progress_pct,
    },
    "summary": {
        "total_checks": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
    },
    "checks": checks,
    "failed_checks": [c["name"] for c in failed],
    "runtime": {
        "window": trend.get("window"),
        "total_runs": trend_metrics.get("total_runs"),
        "successful_runs": trend_metrics.get("successful_runs"),
        "failed_runs": trend_metrics.get("failed_runs"),
        "historical_total_runs": history_summary.get("total_runs"),
        "historical_failed_runs": history_summary.get("failed_runs"),
        "success_rate_pct": trend_metrics.get("success_rate_pct"),
        "avg_duration_sec": trend_metrics.get("avg_duration_sec"),
        "last_duration_sec": trend_metrics.get("last_duration_sec"),
    },
    "decision": {
        "can_continue_shadow": len(failed) == 0,
        "requires_intervention": len(failed) > 0,
        "next_step": "continue_60d_global_preprod" if preprod_safe_nominal and institutional_ready and not failed else ("continue_48h_shadow" if progress_pct < 100 and not failed else "review_shadow_report"),
    },
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
