#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/nsc/app"
PYTHON="/opt/nsc/.venv/bin/python"

# Canonical PREPROD environment
export NSC_ENV="PREPROD"
export NSC_DATA_DIR="${NSC_DATA_DIR:-/opt/nsc/data/preprod}"
export DATA_DIR="$NSC_DATA_DIR"
export NSC_DATA_ROOT="$NSC_DATA_DIR"
export DATA_ROOT="$NSC_DATA_DIR"
export PYTHONPATH="/opt/nsc/app"

OUT="$NSC_DATA_DIR/portfolio/audit/global_preprod_cycle_report.json"
HISTORY_DIR="$NSC_DATA_DIR/portfolio/audit/global_preprod_cycle_history"

cd "$APP_DIR"

STARTED_AT="$(date -Is)"
PIPELINE_RC=0
KERNEL_RC=0
ORCHESTRATOR_RC=0
SYSTEM_METRICS_RC=0

echo "===== NSC GLOBAL PREPROD CYCLE ====="
echo "$STARTED_AT"

echo
echo "----- PHASE 1: MASTER PIPELINE -----"
systemctl start nsc-preprod-pipeline.service || PIPELINE_RC=$?

PIPELINE_RESULT="$(
    systemctl show nsc-preprod-pipeline.service         -p Result         --value         2>/dev/null || echo unknown
)"

PIPELINE_EXEC_STATUS="$(
    systemctl show nsc-preprod-pipeline.service         -p ExecMainStatus         --value         2>/dev/null || echo 1
)"

PIPELINE_ACTIVE_STATE="$(
    systemctl show nsc-preprod-pipeline.service         -p ActiveState         --value         2>/dev/null || echo unknown
)"

PIPELINE_SUB_STATE="$(
    systemctl show nsc-preprod-pipeline.service         -p SubState         --value         2>/dev/null || echo unknown
)"

echo "pipeline_start_rc=$PIPELINE_RC"
echo "pipeline_result=$PIPELINE_RESULT"
echo "pipeline_exec_status=$PIPELINE_EXEC_STATUS"
echo "pipeline_active_state=$PIPELINE_ACTIVE_STATE"
echo "pipeline_sub_state=$PIPELINE_SUB_STATE"

if [[ "$PIPELINE_RC" -ne 0 ]]    || [[ "$PIPELINE_RESULT" != "success" ]]    || [[ "$PIPELINE_EXEC_STATUS" != "0" ]]; then
    echo "ERROR: nsc-preprod-pipeline.service did not complete successfully"
    exit 1
fi

# A successful oneshot must have completed before execution-critical
# phases are allowed to continue.
if [[ "$PIPELINE_ACTIVE_STATE" == "activating" ]]    || [[ "$PIPELINE_ACTIVE_STATE" == "active" ]]; then
    echo "ERROR: nsc-preprod-pipeline.service still running after synchronous start"
    exit 1
fi

echo "PIPELINE_SYNCHRONOUS_COMPLETION=PASS"

systemctl status nsc-preprod-pipeline.service --no-pager -l     | tail -12 || true

echo
echo "----- PHASE 2: KERNEL -----"

systemctl reset-failed nsc-kernel.service || true

# G152_KERNEL_SYNCHRONIZATION_V1
#
# nsc-kernel.service is a oneshot execution-critical phase.
# Start it synchronously: phase 3 must never begin while the kernel is still
# activating/running, and must never accept stale Result metadata.
KERNEL_RC=0

systemctl start nsc-kernel.service || KERNEL_RC=$?

KERNEL_RESULT="$(
    systemctl show nsc-kernel.service         -p Result         --value         2>/dev/null || echo unknown
)"

KERNEL_EXEC_STATUS="$(
    systemctl show nsc-kernel.service         -p ExecMainStatus         --value         2>/dev/null || echo 1
)"

KERNEL_ACTIVE_STATE="$(
    systemctl show nsc-kernel.service         -p ActiveState         --value         2>/dev/null || echo unknown
)"

KERNEL_SUB_STATE="$(
    systemctl show nsc-kernel.service         -p SubState         --value         2>/dev/null || echo unknown
)"

echo "kernel_start_rc=$KERNEL_RC"
echo "kernel_result=$KERNEL_RESULT"
echo "kernel_exec_status=$KERNEL_EXEC_STATUS"
echo "kernel_active_state=$KERNEL_ACTIVE_STATE"
echo "kernel_sub_state=$KERNEL_SUB_STATE"

if [[ "$KERNEL_RC" -ne 0 ]]    || [[ "$KERNEL_RESULT" != "success" ]]    || [[ "$KERNEL_EXEC_STATUS" != "0" ]]; then
    echo "ERROR: nsc-kernel.service did not complete successfully"
    exit 1
fi

# A successful oneshot without RemainAfterExit must be inactive/dead here.
# Most importantly, it must no longer be activating or active.
if [[ "$KERNEL_ACTIVE_STATE" == "activating" ]]    || [[ "$KERNEL_ACTIVE_STATE" == "active" ]]; then
    echo "ERROR: nsc-kernel.service still running after synchronous start"
    exit 1
fi

echo "KERNEL_SYNCHRONOUS_COMPLETION=PASS"

systemctl status nsc-kernel.service   --no-pager   -l   | tail -20   || true

echo
echo "----- PHASE 3: CANONICAL TELEMETRY REFRESH -----"

# G152_SINGLE_ORCHESTRATOR_WRITER_V1
# orchestrator_pro is execution-critical and is produced by nsc-kernel.service
# under User=nsc.  Do not recompute/rewrite it here as root after the kernel.
# This phase refreshes non-authoritative system telemetry only.
ORCHESTRATOR_RC=0
echo "orchestrator_refresh=SKIPPED_KERNEL_IS_CANONICAL_WRITER"

$PYTHON -m src.v2.monitoring.system_metrics_pro \
  || SYSTEM_METRICS_RC=$?

echo "orchestrator_rc=$ORCHESTRATOR_RC"
echo "system_metrics_rc=$SYSTEM_METRICS_RC"

echo
echo "----- PHASE 4: SUPERVISION SUMMARY -----"
SUMMARY_JSON="$($PYTHON src/v2/portfolio/institutional_supervision_summary.py)"
echo "$SUMMARY_JSON" | jq '{
  institutional_layer_ready,
  global_status,
  gate,
  audit
}'

FINISHED_AT="$(date -Is)"

echo
echo "----- PHASE 5: NON-DESTRUCTIVE STRESS TESTS -----"
STRESS_JSON="$($PYTHON src/v2/portfolio/global_preprod_stress_tests.py)"
echo "$STRESS_JSON" | jq '{
  status,
  mode,
  summary,
  failed_scenarios
}'

echo
echo "----- WRITE GLOBAL PREPROD CYCLE REPORT -----"
python3 - <<PY
import json
from pathlib import Path

out = Path("$OUT")
summary = json.loads("""$SUMMARY_JSON""")

report = {
    "status": "ok" if (
        $PIPELINE_RC == 0
        and $KERNEL_RC == 0
        and $ORCHESTRATOR_RC == 0
        and $SYSTEM_METRICS_RC == 0
        and summary.get("institutional_layer_ready")
    ) else "error",
    "engine": "global_preprod_cycle_runner_v1",
    "started_at": "$STARTED_AT",
    "finished_at": "$FINISHED_AT",
    "pipeline_rc": $PIPELINE_RC,
    "kernel_rc": $KERNEL_RC,
    "orchestrator_rc": $ORCHESTRATOR_RC,
    "system_metrics_rc": $SYSTEM_METRICS_RC,
    "institutional_layer_ready": summary.get("institutional_layer_ready"),
    "global_status": summary.get("global_status"),
    "gate": summary.get("gate"),
    "audit": summary.get("audit"),
    "stress_tests": json.loads("""$STRESS_JSON"""),
}

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

history_dir = Path("$HISTORY_DIR")
history_dir.mkdir(parents=True, exist_ok=True)
safe_ts = "$FINISHED_AT".replace(":", "").replace("+", "_").replace("-", "")
history_file = history_dir / f"global_preprod_cycle_{safe_ts}.json"
history_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(json.dumps(report, indent=2))
PY

chown nsc:nsc "$OUT" 2>/dev/null || true
chmod u+rw,g+rw "$OUT" 2>/dev/null || true

echo
echo "----- PHASE 6: HISTORY SUMMARY -----"
$PYTHON src/v2/portfolio/global_preprod_history_summary.py | jq '{
  status,
  summary,
  last_run
}'

echo
echo "----- PHASE 7: TREND MONITOR -----"
$PYTHON src/v2/portfolio/global_preprod_trend_monitor.py | jq '{
  trend_status,
  metrics,
  last_run,
  alerts
}'

echo
echo "----- PHASE 8: ANOMALY DETECTOR -----"
$PYTHON src/v2/portfolio/global_preprod_anomaly_detector.py | jq '{
  anomaly_status,
  summary,
  anomalies
}'

echo
echo "----- PHASE 9: LONG-RUN READINESS -----"
$PYTHON src/v2/portfolio/global_preprod_long_run_readiness.py | jq '{
  readiness_status,
  summary,
  failed_checks,
  decision
}'

echo
echo "----- PHASE 10: 48H SHADOW SUPERVISOR -----"
$PYTHON src/v2/portfolio/global_preprod_48h_shadow_supervisor.py | jq '{
  shadow_status,
  progress,
  summary,
  failed_checks,
  runtime,
  decision
}'

echo
echo "===== NSC GLOBAL PREPROD CYCLE COMPLETED ====="
echo "$FINISHED_AT"
