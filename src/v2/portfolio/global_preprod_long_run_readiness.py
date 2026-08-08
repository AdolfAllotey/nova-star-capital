from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")

HISTORY = BASE / "global_preprod_history_summary.json"
TREND = BASE / "global_preprod_trend_monitor.json"
ANOMALY = BASE / "global_preprod_anomaly_detector.json"
STRESS = BASE / "global_preprod_stress_test_report.json"
GATE = BASE / "supervision_gate.json"

OUT = BASE / "global_preprod_long_run_readiness.json"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_load_error": str(e)}


history = load(HISTORY)
trend = load(TREND)
anomaly = load(ANOMALY)
stress = load(STRESS)
gate = load(GATE)

checks = []

def add_check(name: str, passed: bool, details: dict):
    checks.append({
        "name": name,
        "passed": bool(passed),
        "details": details,
    })

history_summary = history.get("summary") or {}
trend_metrics = trend.get("metrics") or {}
anomaly_summary = anomaly.get("summary") or {}
stress_summary = stress.get("summary") or {}

expected_runtime = trend.get("expected_runtime") or stress.get("expected_runtime") or {}
policy = (gate.get("policy_context") or {})
PREPROD_SAFE_NOMINAL = bool(expected_runtime.get("preprod_safe_nominal")) or (
    policy.get("preprod_safe") is True
    and str(policy.get("action_policy")).upper() == "SIMULATED_ONLY"
    and str(policy.get("execution_mode")).upper() == "SIMULATED"
)
EXPECTED_GATE_MODE = expected_runtime.get("expected_gate_mode") or ("SAFE" if PREPROD_SAFE_NOMINAL else "NORMAL")
EXPECTED_GATE_OPEN = True if PREPROD_SAFE_NOMINAL else True

add_check(
    "minimum_run_history_available",
    int((trend.get("window") or {}).get("actual_window_runs") or history_summary.get("total_runs") or 0) >= 10,
    {
        "window_runs": (trend.get("window") or {}).get("actual_window_runs"),
        "historical_total_runs": history_summary.get("total_runs"),
    },
)

add_check(
    "no_failed_runs",
    int(trend_metrics.get("failed_runs") or 0) == 0,
    {
        "window_failed_runs": trend_metrics.get("failed_runs"),
        "historical_failed_runs": history_summary.get("failed_runs"),
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
    "stress_tests_green",
    stress.get("status") == "ok" and int(stress_summary.get("failed") or 0) == 0,
    {"stress_status": stress.get("status"), "stress_summary": stress_summary},
)

add_check(
    "gate_expected_mode",
    gate.get("gate_open") is EXPECTED_GATE_OPEN and gate.get("mode") == EXPECTED_GATE_MODE,
    {
        "gate_open": gate.get("gate_open"),
        "mode": gate.get("mode"),
        "expected_gate_open": EXPECTED_GATE_OPEN,
        "expected_gate_mode": EXPECTED_GATE_MODE,
        "preprod_safe_nominal": PREPROD_SAFE_NOMINAL,
    },
)

add_check(
    "runtime_duration_stable",
    float(trend_metrics.get("max_duration_sec") or 999) < 60,
    {
        "avg_duration_sec": trend_metrics.get("avg_duration_sec"),
        "max_duration_sec": trend_metrics.get("max_duration_sec"),
        "last_duration_sec": trend_metrics.get("last_duration_sec"),
    },
)

failed = [c for c in checks if not c["passed"]]

payload = {
    "status": "ok",
    "engine": "global_preprod_long_run_readiness_v1_2_preprod_safe_nominal",
    "window": trend.get("window"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "expected_runtime": {
        "preprod_safe_nominal": PREPROD_SAFE_NOMINAL,
        "expected_gate_mode": EXPECTED_GATE_MODE,
        "expected_gate_open": EXPECTED_GATE_OPEN,
    },
    "readiness_status": "READY" if not failed else "NOT_READY",
    "summary": {
        "total_checks": len(checks),
        "passed": len(checks) - len(failed),
        "failed": len(failed),
    },
    "checks": checks,
    "failed_checks": [c["name"] for c in failed],
    "decision": {
        "can_start_long_run": not failed,
        "recommended_next_step": "48h_shadow_preprod" if not failed else "fix_failed_readiness_checks",
    },
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
