from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
TREND = BASE / "global_preprod_trend_monitor.json"
HISTORY = BASE / "global_preprod_history_summary.json"
GATE = BASE / "supervision_gate.json"
OUT = BASE / "global_preprod_anomaly_detector.json"

def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_load_error": str(e)}

trend = load(TREND)
history = load(HISTORY)
gate = load(GATE)

expected_runtime = trend.get("expected_runtime") or {}
policy = gate.get("policy_context") or {}

PREPROD_SAFE_NOMINAL = bool(expected_runtime.get("preprod_safe_nominal")) or (
    policy.get("preprod_safe") is True
    and str(policy.get("action_policy")).upper() == "SIMULATED_ONLY"
    and str(policy.get("execution_mode")).upper() == "SIMULATED"
)
EXPECTED_GATE_MODE = expected_runtime.get("expected_gate_mode") or ("SAFE" if PREPROD_SAFE_NOMINAL else "NORMAL")

metrics = trend.get("metrics") or {}
last_run = trend.get("last_run") or {}
history_summary = history.get("summary") or {}

anomalies = []

success_rate = float(metrics.get("success_rate_pct") or 0)
failed_runs = int(metrics.get("failed_runs") or 0)
degraded_runs = int(metrics.get("degraded_runs") or 0)
avg_duration = float(metrics.get("avg_duration_sec") or 0)
max_duration = float(metrics.get("max_duration_sec") or 0)
last_duration = float(metrics.get("last_duration_sec") or 0)

if success_rate < 95:
    anomalies.append({
        "type": "success_rate_drift",
        "severity": "warning",
        "value": success_rate,
        "threshold": 95,
    })

if failed_runs > 0:
    anomalies.append({
        "type": "failed_runs_detected",
        "severity": "warning",
        "value": failed_runs,
        "threshold": 0,
    })

if degraded_runs > 0:
    anomalies.append({
        "type": "degraded_runs_detected",
        "severity": "info",
        "value": degraded_runs,
        "threshold": 0,
    })

if avg_duration > 30:
    anomalies.append({
        "type": "avg_duration_slow",
        "severity": "warning",
        "value": avg_duration,
        "threshold": 30,
    })

if max_duration > 60:
    anomalies.append({
        "type": "max_duration_abnormal",
        "severity": "critical",
        "value": max_duration,
        "threshold": 60,
    })

if last_duration > max(45, avg_duration * 2 if avg_duration else 45):
    anomalies.append({
        "type": "last_run_duration_spike",
        "severity": "warning",
        "value": last_duration,
        "threshold": max(45, avg_duration * 2 if avg_duration else 45),
    })

if str(last_run.get("gate_mode")).upper() != str(EXPECTED_GATE_MODE).upper():
    anomalies.append({
        "type": "gate_mode_drift",
        "severity": "critical",
        "value": last_run.get("gate_mode"),
        "expected": EXPECTED_GATE_MODE,
    })

if int(last_run.get("stress_failed") or 0) > 0:
    anomalies.append({
        "type": "stress_failure_drift",
        "severity": "critical",
        "value": last_run.get("stress_failed"),
        "threshold": 0,
        "source": last_run.get("stress_source") or "trend_last_run",
    })

critical = [a for a in anomalies if a.get("severity") == "critical"]
warning = [a for a in anomalies if a.get("severity") == "warning"]
info = [a for a in anomalies if a.get("severity") == "info"]

payload = {
    "status": "ok",
    "engine": "global_preprod_anomaly_detector_v1_3_preprod_safe_nominal",
    "window": trend.get("window"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "expected_runtime": {
        "preprod_safe_nominal": PREPROD_SAFE_NOMINAL,
        "expected_gate_mode": EXPECTED_GATE_MODE,
    },
    "anomaly_status": "CRITICAL" if critical else "WARNING" if warning else "INFO" if info else "CLEAR",
    "summary": {
        "total_anomalies": len(anomalies),
        "critical": len(critical),
        "warning": len(warning),
        "info": len(info),
    },
    "inputs": {
        "trend_status": trend.get("trend_status"),
        "history_status": history.get("status"),
        "total_runs": history_summary.get("total_runs"),
    },
    "metrics": metrics,
    "anomalies": anomalies,
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
