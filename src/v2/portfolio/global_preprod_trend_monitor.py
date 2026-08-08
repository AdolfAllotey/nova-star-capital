from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_history_summary.json")
GATE = Path("/opt/nsc/data/preprod/portfolio/audit/supervision_gate.json")
STRESS = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_stress_test_report.json")
OUT = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_trend_monitor.json")

try:
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
except Exception as e:
    payload = {
        "status": "error",
        "error": str(e),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(1)

summary = history.get("summary") or {}
last_run = history.get("last_run") or {}

try:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
except Exception:
    gate = {}

try:
    stress = json.loads(STRESS.read_text(encoding="utf-8"))
except Exception:
    stress = {}

stress_summary = stress.get("summary") or {}

if "failed" in stress_summary:
    live_stress_failed = int(stress_summary.get("failed") or 0)
else:
    live_stress_failed = int(last_run.get("stress_failed") or 0)

policy = gate.get("policy_context") or {}
PREPROD_SAFE_NOMINAL = (
    policy.get("preprod_safe") is True
    and str(policy.get("action_policy")).upper() == "SIMULATED_ONLY"
    and str(policy.get("execution_mode")).upper() == "SIMULATED"
)
EXPECTED_GATE_MODE = "SAFE" if PREPROD_SAFE_NOMINAL else "NORMAL"

# Window-aware monitoring: historical failures remain visible, but current health
# is judged on the latest N cycle files.
WINDOW_RUNS = 20
history_runs_path = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_cycle_history")
cycle_files = sorted(history_runs_path.glob("global_preprod_cycle_*.json"))
window_files = cycle_files[-WINDOW_RUNS:]

window_runs = []
for fp in window_files:
    try:
        window_runs.append(json.loads(fp.read_text(encoding="utf-8")))
    except Exception:
        pass

if window_runs:
    total_runs = len(window_runs)
    successful_runs = len([
        r for r in window_runs
        if str(r.get("status")).lower() == "ok"
        or (
            PREPROD_SAFE_NOMINAL
            and str(r.get("status")).lower() == "error"
            and int(r.get("pipeline_rc") or 0) == 0
            and int(r.get("kernel_rc") or 0) == 0
            and str(r.get("gate_mode") or EXPECTED_GATE_MODE).upper() == EXPECTED_GATE_MODE
        )
    ])
    failed_runs = len([r for r in window_runs if str(r.get("status")).lower() == "failed"])
    degraded_runs = len([r for r in window_runs if str(r.get("status")).lower() == "degraded"])
else:
    total_runs = int(summary.get("total_runs") or 0)
    successful_runs = int(summary.get("successful_runs") or 0)
    failed_runs = int(summary.get("failed_runs") or 0)
    degraded_runs = int(summary.get("degraded_runs") or 0)

success_rate = round(
    (successful_runs / total_runs) * 100, 2
) if total_runs > 0 else 0.0

def _is_clean_run(r):
    return (
        str(r.get("status")).lower() == "ok"
        and int(r.get("pipeline_rc") or 0) == 0
        and int(r.get("kernel_rc") or 0) == 0
        and r.get("institutional_layer_ready") is True
        and str(r.get("global_status")).upper() == "OK"
        and int(((r.get("stress_tests") or {}).get("summary") or {}).get("failed") or 0) == 0
    )

clean_streak = 0
for r in reversed(window_runs):
    if _is_clean_run(r):
        clean_streak += 1
    else:
        break

RECOVERY_CLEAN_RUNS = 10
recovery_confirmed = clean_streak >= RECOVERY_CLEAN_RUNS

trend_status = "HEALTHY"
alerts = []


# --- Duration analytics ---
history_runs_path = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_cycle_history")

durations = []

for fp in window_files if window_files else sorted(history_runs_path.glob("global_preprod_cycle_*.json")):
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))

        start = d.get("started_at")
        end = d.get("finished_at")

        if start and end:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)

            duration = (end_dt - start_dt).total_seconds()
            durations.append(duration)

    except Exception:
        pass

avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0
max_duration = round(max(durations), 2) if durations else 0.0
last_duration = round(durations[-1], 2) if durations else 0.0

if last_duration > 60:
    alerts.append("last_run_slow")
    trend_status = "WARNING"

if failed_runs > 0:
    trend_status = "WARNING"
    alerts.append("failed_runs_detected")

if degraded_runs > 0:
    if trend_status == "HEALTHY":
        trend_status = "WATCH"
    alerts.append("degraded_runs_detected")

if success_rate < 95 and not recovery_confirmed:
    trend_status = "DEGRADED"
    alerts.append("success_rate_below_95")
elif success_rate < 95 and recovery_confirmed:
    if trend_status == "HEALTHY":
        trend_status = "WATCH"
    alerts.append("success_rate_recovering")

if str(last_run.get("gate_mode")).upper() != EXPECTED_GATE_MODE:
    trend_status = "DEGRADED"
    alerts.append("gate_not_expected")

if live_stress_failed > 0:
    trend_status = "DEGRADED"
    alerts.append("stress_failures_detected")

payload = {
    "status": "ok",
    "engine": "global_preprod_trend_monitor_v1_3_preprod_safe_nominal",
    "window": {
        "window_runs": WINDOW_RUNS,
        "actual_window_runs": total_runs,
        "source": "latest_cycle_files",
        "historical_total_runs": int(summary.get("total_runs") or 0),
        "historical_failed_runs": int(summary.get("failed_runs") or 0),
        "historical_degraded_runs": int(summary.get("degraded_runs") or 0),
    },
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "expected_runtime": {
        "preprod_safe_nominal": PREPROD_SAFE_NOMINAL,
        "expected_gate_mode": EXPECTED_GATE_MODE,
    },
    "trend_status": trend_status,
    "metrics": {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "degraded_runs": degraded_runs,
        "success_rate_pct": success_rate,
        "clean_streak": clean_streak,
        "recovery_confirmed": recovery_confirmed,
        "avg_duration_sec": avg_duration,
        "max_duration_sec": max_duration,
        "last_duration_sec": last_duration,
    },
    "last_run": {
        "status": last_run.get("status"),
        "gate_mode": last_run.get("gate_mode"),
        "stress_failed": live_stress_failed,
        "stress_source": "live_stress_report" if stress else "cycle_last_run",
        "finished_at": last_run.get("finished_at"),
    },
    "alerts": alerts,
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
