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
PROVIDER_RC=0
CUTOVER_DRY_RUN_RC=0
CUTOVER_EXECUTE_RC=0
PIPELINE_RC=0
KERNEL_RC=0
ORCHESTRATOR_RC=0
SYSTEM_METRICS_RC=0

OFFENSIVE_ROOT="$NSC_DATA_DIR/equities_offensive"
CUTOVER_SCRIPT="$APP_DIR/src/v2/equities_offensive/cutover/four_artifact_cutover_v2.py"
CUTOVER_DRY_RUN_JSON="$(mktemp)"
CUTOVER_EXECUTE_JSON=""

cleanup_global_cycle() {
    rm -f "$CUTOVER_DRY_RUN_JSON"

    if [[ -n "$CUTOVER_EXECUTE_JSON" ]]; then
        rm -f "$CUTOVER_EXECUTE_JSON"
    fi
}
trap cleanup_global_cycle EXIT

echo "===== NSC GLOBAL PREPROD CYCLE ====="
echo "$STARTED_AT"

echo
echo "----- PHASE 0A: OFFENSIVE PROVIDER REFRESH -----"

PROVIDER_VALIDATION="$OFFENSIVE_ROOT/market/providers/provider_validation_run_v1.json"
PROVIDER_TRIGGERED_AT="$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)"

PROVIDER_SHA_BEFORE=""
if [[ -f "$PROVIDER_VALIDATION" ]]; then
    PROVIDER_SHA_BEFORE="$(sha256sum "$PROVIDER_VALIDATION" | awk '{print $1}')"
fi

systemctl reset-failed nsc-equities-provider-refresh.service || true
systemctl start nsc-equities-provider-refresh.service || PROVIDER_RC=$?

PROVIDER_RESULT="$(
    systemctl show nsc-equities-provider-refresh.service \
        -p Result --value 2>/dev/null || echo unknown
)"

PROVIDER_EXEC_STATUS="$(
    systemctl show nsc-equities-provider-refresh.service \
        -p ExecMainStatus --value 2>/dev/null || echo 1
)"

PROVIDER_ACTIVE_STATE="$(
    systemctl show nsc-equities-provider-refresh.service \
        -p ActiveState --value 2>/dev/null || echo unknown
)"

PROVIDER_SHA_AFTER=""
if [[ -f "$PROVIDER_VALIDATION" ]]; then
    PROVIDER_SHA_AFTER="$(sha256sum "$PROVIDER_VALIDATION" | awk '{print $1}')"
fi

echo "provider_triggered_at=$PROVIDER_TRIGGERED_AT"
echo "provider_sha_before=$PROVIDER_SHA_BEFORE"
echo "provider_sha_after=$PROVIDER_SHA_AFTER"
echo "provider_start_rc=$PROVIDER_RC"
echo "provider_result=$PROVIDER_RESULT"
echo "provider_exec_status=$PROVIDER_EXEC_STATUS"
echo "provider_active_state=$PROVIDER_ACTIVE_STATE"

if [[ "$PROVIDER_RC" -ne 0 ]] \
    || [[ "$PROVIDER_RESULT" != "success" ]] \
    || [[ "$PROVIDER_EXEC_STATUS" != "0" ]]; then
    echo "ERROR: provider refresh did not complete technically"
    exit 1
fi

if [[ "$PROVIDER_ACTIVE_STATE" == "activating" ]] \
    || [[ "$PROVIDER_ACTIVE_STATE" == "active" ]]; then
    echo "ERROR: provider refresh still running after synchronous start"
    exit 1
fi

if [[ -z "$PROVIDER_SHA_AFTER" ]]; then
    echo "ERROR: provider validation artefact missing"
    exit 1
fi

if [[ "$PROVIDER_SHA_AFTER" == "$PROVIDER_SHA_BEFORE" ]]; then
    echo "ERROR: provider validation artefact was not regenerated"
    exit 1
fi

"$PYTHON" - "$PROVIDER_VALIDATION" "$PROVIDER_TRIGGERED_AT" <<'PY_PROVIDER'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])

triggered_at = datetime.fromisoformat(
    sys.argv[2].replace("Z", "+00:00")
).astimezone(timezone.utc)

payload = json.loads(path.read_text(encoding="utf-8"))

started_at = datetime.fromisoformat(
    payload["started_at"].replace("Z", "+00:00")
).astimezone(timezone.utc)

generated_at = datetime.fromisoformat(
    payload["generated_at"].replace("Z", "+00:00")
).astimezone(timezone.utc)

if started_at < triggered_at:
    raise SystemExit(
        "provider artefact predates this Global provider trigger"
    )

if generated_at < started_at:
    raise SystemExit(
        "provider generated_at predates provider started_at"
    )

if payload.get("status") != "quality_gate_passed":
    raise SystemExit(
        f"unexpected provider status: {payload.get('status')!r}"
    )

if payload.get("quality_gate_decision") != "PASS":
    raise SystemExit(
        "provider quality gate decision is not PASS"
    )

if payload.get("canonical_files_modified") is not False:
    raise SystemExit(
        "provider reports canonical files modified"
    )

if payload.get("promotion_executed") is not False:
    raise SystemExit(
        "provider reports promotion executed"
    )

print("PROVIDER_DURABLE_CAUSAL_EVIDENCE=PASS")
PY_PROVIDER

echo "PROVIDER_NEW_ARTIFACT=PASS"
echo "PROVIDER_SYNCHRONOUS_COMPLETION=PASS"

echo
echo "----- PHASE 0B: FOUR-ARTIFACT CUTOVER DRY-RUN -----"

set +e
"$PYTHON" "$CUTOVER_SCRIPT"     --root "$OFFENSIVE_ROOT"     >"$CUTOVER_DRY_RUN_JSON"
CUTOVER_DRY_RUN_RC=$?
set -e

echo "cutover_dry_run_rc=$CUTOVER_DRY_RUN_RC"

if [[ "$CUTOVER_DRY_RUN_RC" -ne 0 ]]; then
    echo "ERROR: no admissible Offensive canonical cutover candidate"
    cat "$CUTOVER_DRY_RUN_JSON" || true
    exit 1
fi

AUTHORIZATION_DIGEST="$(
    "$PYTHON" - "$CUTOVER_DRY_RUN_JSON" <<'PY_DIGEST'
import json
import sys
from pathlib import Path

payload = json.loads(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

if payload.get("status") != "candidate_ready":
    raise SystemExit(
        "cutover dry-run status is not candidate_ready"
    )

if payload.get("cutover_executed") is not False:
    raise SystemExit(
        "dry-run unexpectedly reports cutover execution"
    )

if payload.get("active_files_modified") is not False:
    raise SystemExit(
        "dry-run unexpectedly reports active file modification"
    )

authorization = payload.get("authorization")

if not isinstance(authorization, dict):
    raise SystemExit("authorization payload missing")

digest = str(authorization.get("digest") or "").strip().lower()

if len(digest) != 64:
    raise SystemExit("authorization digest invalid")

if any(c not in "0123456789abcdef" for c in digest):
    raise SystemExit("authorization digest is not hexadecimal")

print(digest)
PY_DIGEST
)"

echo "CUTOVER_DRY_RUN=PASS"
echo "CUTOVER_AUTHORIZATION_DIGEST=$AUTHORIZATION_DIGEST"

echo
echo "----- PHASE 0C: FOUR-ARTIFACT CUTOVER EXECUTE -----"

CUTOVER_EXECUTE_JSON="$(
    mktemp /tmp/nsc-cutover-execute.XXXXXX.json
)"

set +e
"$PYTHON" "$CUTOVER_SCRIPT" \
    --root "$OFFENSIVE_ROOT" \
    --execute \
    --authorization-digest "$AUTHORIZATION_DIGEST" \
    > "$CUTOVER_EXECUTE_JSON"
CUTOVER_EXECUTE_RC=$?
set -e

echo "cutover_execute_rc=$CUTOVER_EXECUTE_RC"

if [[ "$CUTOVER_EXECUTE_RC" -ne 0 ]]; then
    echo "ERROR: four-artifact cutover execute failed"
    cat "$CUTOVER_EXECUTE_JSON"
    exit 1
fi

"$PYTHON" - \
    "$CUTOVER_EXECUTE_JSON" \
    "$AUTHORIZATION_DIGEST" <<'PYEXEC'
import json
import re
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
expected_digest = sys.argv[2].strip()

if not re.fullmatch(
    r"[0-9a-f]{64}",
    expected_digest,
):
    raise SystemExit(
        "cutover execute expected digest is invalid"
    )

try:
    payload = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )
except Exception as exc:
    raise SystemExit(
        f"cutover execute JSON parse failed: {exc}"
    )

if not isinstance(payload, dict):
    raise SystemExit(
        "cutover execute report is not an object"
    )

if payload.get("status") != "committed":
    raise SystemExit(
        "cutover execute status is not committed"
    )

if payload.get("mode") != "execute":
    raise SystemExit(
        "cutover execute mode is not execute"
    )

if payload.get("cutover_executed") is not True:
    raise SystemExit(
        "cutover execute did not confirm execution"
    )

if payload.get("active_files_modified") is not True:
    raise SystemExit(
        "cutover execute did not confirm active modification"
    )

authorized_digest = str(
    payload.get("authorized_digest")
    or ""
).strip()

if authorized_digest != expected_digest:
    raise SystemExit(
        "cutover execute authorized_digest mismatch"
    )

authorization = payload.get("authorization")

if not isinstance(authorization, dict):
    raise SystemExit(
        "cutover execute authorization object missing"
    )

report_digest = str(
    authorization.get("digest")
    or ""
).strip()

if report_digest != expected_digest:
    raise SystemExit(
        "cutover execute authorization.digest mismatch"
    )

print("CUTOVER_EXECUTE_REPORT=PASS")
print(
    f"CUTOVER_EXECUTE_AUTHORIZED_DIGEST={authorized_digest}"
)
PYEXEC

rm -f "$CUTOVER_EXECUTE_JSON"
CUTOVER_EXECUTE_JSON=""

echo "FOUR_ARTIFACT_CUTOVER=PASS"

echo
echo "----- PHASE 0D: CRYPTO CAPITAL PRE-MASTER PREPARATION -----"

# The Master consumes the Crypto portfolio input before the Kernel runs.
# Refresh the Crypto capital allocation here so the Master never depends on
# a stale artifact from a previous Kernel cycle.
#
# Fail closed if the static V1 Crypto config diverges from the governed
# capital_pools authority.  Do not silently refresh a semantically stale
# allocation.

"$PYTHON" - <<'PYCRYPTOAUTH'
import json
from pathlib import Path

root = Path("/opt/nsc/data/preprod")
cfg_path = root / "trading/capital_config.json"
pools_path = root / "capital/capital_pools.json"

cfg = json.loads(cfg_path.read_text())
pools = json.loads(pools_path.read_text())

assert pools.get("env") == "PREPROD", "capital pools env is not PREPROD"
assert pools.get("real_money_enabled") is False, "real money unexpectedly enabled"
assert pools.get("broker_connection_enabled") is False, "broker connection unexpectedly enabled"

crypto = pools["pools"]["crypto_exchange_pool"]

cfg_total = float(cfg["total_budget"])
pool_total = float(crypto["total_eur"])

assert cfg.get("capital_source") == \
    "capital_pools.crypto_exchange_pool.total_eur", \
    "unexpected Crypto capital source"

assert abs(cfg_total - pool_total) < 0.01, \
    f"Crypto capital mismatch: config={cfg_total} pool={pool_total}"

assert cfg.get("broker_split") == crypto.get("brokers"), \
    "Crypto broker split diverges from capital pools"

assert float(cfg.get("trading_ratio", 0)) > 0, \
    "invalid Crypto trading_ratio"

assert int(cfg.get("max_positions", 0)) > 0, \
    "invalid Crypto max_positions"

print(f"CRYPTO_CAPITAL_AUTHORITY=PASS total_eur={pool_total:.2f}")
PYCRYPTOAUTH

CRYPTO_ALLOC="$DATA_DIR/trading/capital_allocation.json"
CRYPTO_ALLOC_MTIME_BEFORE="$(
    stat -c '%y' "$CRYPTO_ALLOC" 2>/dev/null || true
)"

"$PYTHON" -m src.v2.analysis.capital_allocator

if [[ ! -f "$CRYPTO_ALLOC" ]]; then
    echo "ERROR: Crypto capital allocation was not produced"
    exit 1
fi

CRYPTO_ALLOC_MTIME_AFTER="$(
    stat -c '%y' "$CRYPTO_ALLOC"
)"

if [[ -n "$CRYPTO_ALLOC_MTIME_BEFORE" ]] \
   && [[ "$CRYPTO_ALLOC_MTIME_AFTER" == "$CRYPTO_ALLOC_MTIME_BEFORE" ]]; then
    echo "ERROR: Crypto capital allocation mtime did not advance"
    exit 1
fi

echo "CRYPTO_CAPITAL_ALLOCATION_REGENERATED=PASS"

"$PYTHON" - <<'PYCRYPTOALLOC'
import json
from pathlib import Path

root = Path("/opt/nsc/data/preprod")

cfg = json.loads(
    (root / "trading/capital_config.json").read_text()
)
pools = json.loads(
    (root / "capital/capital_pools.json").read_text()
)
d = json.loads(
    (root / "trading/capital_allocation.json").read_text()
)

crypto = pools["pools"]["crypto_exchange_pool"]

expected_total = float(crypto["total_eur"])
expected_ratio = float(cfg["trading_ratio"])
expected_positions = int(cfg["max_positions"])
expected_trading = round(expected_total * expected_ratio, 2)
expected_per_trade = (
    round(expected_trading / expected_positions, 2)
    if expected_positions > 0 else 0.0
)

assert abs(float(d["total_budget"]) - expected_total) < 0.01
assert abs(float(d["trading_budget"]) - expected_trading) < 0.01
assert abs(float(d["capital_per_trade"]) - expected_per_trade) < 0.01
assert int(d["max_positions"]) == expected_positions

assert set(d["strategy_weights"]) == {
    "momentum", "sniper", "whale"
}

assert d["strategy_weights_source"] == \
    "static_v1_legacy_portfolio_observation_contract"

assert d["emotional_regime"] == "not_applicable"
assert d["emotional_action"] == "not_applicable"

print(
    "CRYPTO_CAPITAL_ALLOCATION_CONTRACT=PASS "
    f"total={expected_total:.2f} "
    f"trading={expected_trading:.2f} "
    f"per_trade={expected_per_trade:.2f} "
    f"max_positions={expected_positions}"
)
PYCRYPTOALLOC

echo "CRYPTO_PREMASTER_PREPARATION=PASS"

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
OUT="$OUT" \
SUMMARY_JSON="$SUMMARY_JSON" \
PIPELINE_RC="$PIPELINE_RC" \
KERNEL_RC="$KERNEL_RC" \
ORCHESTRATOR_RC="$ORCHESTRATOR_RC" \
SYSTEM_METRICS_RC="$SYSTEM_METRICS_RC" \
STARTED_AT="$STARTED_AT" \
FINISHED_AT="$FINISHED_AT" \
STRESS_JSON="$STRESS_JSON" \
HISTORY_DIR="$HISTORY_DIR" \
python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["OUT"])
summary = json.loads(os.environ["SUMMARY_JSON"])

pipeline_rc = int(os.environ["PIPELINE_RC"])
kernel_rc = int(os.environ["KERNEL_RC"])
orchestrator_rc = int(os.environ["ORCHESTRATOR_RC"])
system_metrics_rc = int(os.environ["SYSTEM_METRICS_RC"])
started_at = os.environ["STARTED_AT"]
finished_at = os.environ["FINISHED_AT"]
stress_tests = json.loads(os.environ["STRESS_JSON"])
history_dir = Path(os.environ["HISTORY_DIR"])

report = {
    "status": "ok" if (
        pipeline_rc == 0
        and kernel_rc == 0
        and orchestrator_rc == 0
        and system_metrics_rc == 0
        and summary.get("institutional_layer_ready")
    ) else "error",
    "engine": "global_preprod_cycle_runner_v1",
    "started_at": started_at,
    "finished_at": finished_at,
    "pipeline_rc": pipeline_rc,
    "kernel_rc": kernel_rc,
    "orchestrator_rc": orchestrator_rc,
    "system_metrics_rc": system_metrics_rc,
    "institutional_layer_ready": summary.get("institutional_layer_ready"),
    "global_status": summary.get("global_status"),
    "gate": summary.get("gate"),
    "audit": summary.get("audit"),
    "stress_tests": stress_tests,
}

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

history_dir.mkdir(parents=True, exist_ok=True)
safe_ts = finished_at.replace(":", "").replace("+", "_").replace("-", "")
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
