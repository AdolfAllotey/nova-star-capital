# /opt/nsc/app/scripts/smoke_preprod.sh
# Smoke test PREPROD: vérifie que le kernel ne “blocked” pas le plan en régime normal,
# et que la boucle arrive au SUMMARY.
#
# Usage:
#   chmod +x scripts/smoke_preprod.sh
#   ./scripts/smoke_preprod.sh
#
# Options:
#   NSC_VERBOSE=1   -> affiche plus de logs
#   NSC_FAIL_FAST=1 -> stop dès qu’un check échoue (par défaut oui)

set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/opt/nsc/app}"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"
PLAN="$DATA_DIR/trading/execution_plan.json"
RISK="$DATA_DIR/analysis/risk_engine_pro.json"
SQ="$DATA_DIR/analysis/signal_quality_engine_pro.json"

VERBOSE="${NSC_VERBOSE:-0}"
FAIL_FAST="${NSC_FAIL_FAST:-1}"

cd "$ROOT_DIR"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "❌ Missing command: $1"
    exit 2
  }
}

need_cmd python
need_cmd jq

log() { echo "➡️  $*"; }
ok()  { echo "✅ $*"; }
warn(){ echo "⚠️  $*"; }
die() { echo "❌ $*"; exit 1; }

jq_get() {
  local file="$1" expr="$2"
  jq -er "$expr" "$file" 2>/dev/null
}

assert_file() {
  [[ -f "$1" ]] || die "File not found: $1"
}

run_cmd() {
  if [[ "$VERBOSE" == "1" ]]; then
    "$@"
  else
    "$@" >/dev/null 2>&1
  fi
}

# --- Step 0: Run execution engine to generate a baseline plan
log "Running execution_engine_pro to generate baseline execution_plan.json"
run_cmd python -m src.v2.analysis.execution_engine_pro || true
assert_file "$PLAN"

BASE_WRITER="$(jq_get "$PLAN" '.writer // ""' || echo "")"
BASE_STATUS="$(jq_get "$PLAN" '.status // ""' || echo "")"
BASE_ORDERS_LEN="$(jq_get "$PLAN" '(.orders // []) | length' || echo "0")"

log "Baseline plan: writer=$BASE_WRITER status=$BASE_STATUS orders_len=$BASE_ORDERS_LEN"
[[ "$BASE_ORDERS_LEN" -ge 0 ]] || die "Baseline orders_len invalid"

# --- Step 1: Run trading_kernel and capture output (need SUMMARY presence)
log "Running trading_kernel and capturing output"
KERNEL_OUT="$(mktemp)"
set +e
python -m src.v2.trading.trading_kernel 2>&1 | tee "$KERNEL_OUT" >/dev/null
KERNEL_RC="${PIPESTATUS[0]}"
set -e

# Kernel may return non-zero in some safety paths; we key on SUMMARY/plan integrity.
if [[ "$VERBOSE" == "1" ]]; then
  log "trading_kernel rc=$KERNEL_RC (non-zero tolerated if SUMMARY present & plan OK)"
fi

# Must contain SUMMARY line
if ! grep -q "\[trading_kernel\]\[SUMMARY\]" "$KERNEL_OUT"; then
  echo "---- last 200 lines ----"
  tail -n 200 "$KERNEL_OUT" || true
  die "Missing [trading_kernel][SUMMARY] => run did not complete the full loop"
fi
ok "Kernel produced SUMMARY"

# --- Step 2: Read resulting plan
assert_file "$PLAN"

AFTER_WRITER="$(jq_get "$PLAN" '.writer // ""' || echo "")"
AFTER_STATUS="$(jq_get "$PLAN" '.status // ""' || echo "")"
AFTER_ORDERS_LEN="$(jq_get "$PLAN" '(.orders // []) | length' || echo "0")"

log "After kernel plan: writer=$AFTER_WRITER status=$AFTER_STATUS orders_len=$AFTER_ORDERS_LEN"

# --- Step 3: Read risk + signal quality (must exist after run)
assert_file "$RISK"
assert_file "$SQ"

RISK_FLAG="$(jq_get "$RISK" '(.flag // .global_flag // "") | ascii_downcase' || echo "")"
RISK_SCORE="$(jq_get "$RISK" '(.score // .risk_score // 0) | tonumber' || echo "0")"

SQ_FLAG="$(jq_get "$SQ" '(.flag // "") | ascii_downcase' || echo "")"
SQ_SCORE="$(jq_get "$SQ" '(.score // 0) | tonumber' || echo "0")"
SQ_HARD="$(jq_get "$SQ" '(.hard_block // false) | tostring' || echo "false")"

log "risk_engine_pro: flag=$RISK_FLAG score=$RISK_SCORE"
log "signal_quality: flag=$SQ_FLAG score=$SQ_SCORE hard_block=$SQ_HARD"

# --- Step 4: Checks

# 4.1 Plan must not be blocked when risk_on + SQ ok
if [[ "$RISK_FLAG" == "risk_on" && "$SQ_FLAG" == "ok" && "$SQ_HARD" == "false" ]]; then
  if [[ "$AFTER_STATUS" == "blocked" || "$AFTER_ORDERS_LEN" -eq 0 ]]; then
    echo "---- kernel block/gate lines ----"
    egrep -i "hard_block|blocked|kill_switch|veto|gate|fatal|abort|skip|stop|preserve" "$KERNEL_OUT" | tail -n 200 || true
    die "Inconsistent: risk_on + SQ ok, but execution_plan is blocked/empty (status=$AFTER_STATUS orders_len=$AFTER_ORDERS_LEN)"
  fi
  ok "Plan is not blocked under normal conditions (risk_on + SQ ok)"
else
  warn "risk/sq not in normal (risk_on+ok) => skipping 'must not block' invariant"
fi

# 4.2 If kernel overwrote plan with trading_kernel/blocked, it must be justified by hard gating
if [[ "$AFTER_WRITER" == "trading_kernel" && "$AFTER_STATUS" == "blocked" ]]; then
  # Accept only if risk_off/emergency/off OR risk_score<=35 OR SQ hard_block/flag hard_block
  must_ok="0"
  # numeric compare via awk to avoid locale issues
  if [[ "$RISK_FLAG" == "risk_off" || "$RISK_FLAG" == "off" || "$RISK_FLAG" == "emergency" ]]; then must_ok="1"; fi
  if awk "BEGIN{exit !($RISK_SCORE <= 35.0)}"; then must_ok="1"; fi
  if [[ "$SQ_HARD" == "true" || "$SQ_FLAG" == "hard_block" ]]; then must_ok="1"; fi

  if [[ "$must_ok" != "1" ]]; then
    die "Kernel produced blocked plan without a valid hard-gate condition (risk_flag=$RISK_FLAG risk_score=$RISK_SCORE sq_flag=$SQ_FLAG sq_hard=$SQ_HARD)"
  fi
  ok "Blocked plan is justified by hard-gate inputs"
fi

# 4.3 Orders len should never increase beyond max_orders_per_run if present
RL_FILE="$DATA_DIR/trading/risk_limits.json"
if [[ -f "$RL_FILE" ]]; then
  MAX_ORDERS="$(jq_get "$RL_FILE" '(.max_orders_per_run // 0) | tonumber' || echo "0")"
  if [[ "$MAX_ORDERS" -gt 0 ]]; then
    if [[ "$AFTER_ORDERS_LEN" -gt "$MAX_ORDERS" ]]; then
      die "orders_len=$AFTER_ORDERS_LEN exceeds risk_limits.max_orders_per_run=$MAX_ORDERS"
    fi
    ok "orders_len respects max_orders_per_run ($AFTER_ORDERS_LEN <= $MAX_ORDERS)"
  fi
fi

# 4.4 Baseline vs after: if kernel is healthy, it should not nuke a valid baseline plan (unless justified)
if [[ "$BASE_STATUS" == "ok" && "$BASE_ORDERS_LEN" -gt 0 ]]; then
  if [[ "$AFTER_STATUS" == "blocked" || "$AFTER_ORDERS_LEN" -eq 0 ]]; then
    # Allowed only if justified by gating
    if [[ "$RISK_FLAG" == "risk_off" || "$RISK_FLAG" == "off" || "$RISK_FLAG" == "emergency" ]] \
       || awk "BEGIN{exit !($RISK_SCORE <= 35.0)}" \
       || [[ "$SQ_HARD" == "true" || "$SQ_FLAG" == "hard_block" ]]; then
      warn "Kernel replaced a valid baseline plan due to hard-gate conditions (acceptable)"
    else
      die "Kernel nuked a valid baseline plan without hard-gate conditions"
    fi
  else
    ok "Kernel preserved a valid baseline plan (or produced a valid one)"
  fi
fi

rm -f "$KERNEL_OUT" || true
ok "SMOKE PREPROD PASSED"
