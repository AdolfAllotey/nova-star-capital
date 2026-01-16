#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/nsc/app}"
DATA_DIR="${DATA_DIR:-$APP_ROOT/data/trading}"
LOG_DIR="${LOG_DIR:-$APP_ROOT/logs}"

KILL_SWITCH_FILE="${KILL_SWITCH_FILE:-$DATA_DIR/kill_switch.json}"
EXEC_PLAN_FILE="${EXEC_PLAN_FILE:-$DATA_DIR/execution_plan.json}"
OPEN_POS_FILE="${OPEN_POS_FILE:-$DATA_DIR/open_positions.json}"
SIM_FILLS_FILE="${SIM_FILLS_FILE:-$DATA_DIR/simulated_fills.json}"

fail() { echo "❌ [FAIL] $*" >&2; exit 1; }
warn() { echo "⚠️  [WARN] $*" >&2; }
ok()   { echo "✅ [OK] $*"; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"; }
need_file() { [[ -f "$1" ]] || fail "Missing required file: $1"; }
json_valid() { jq -e . "$1" >/dev/null 2>&1; }

need_cmd jq
need_cmd grep

cd "$APP_ROOT"

ENV="${NSC_ENV:-UNKNOWN}"
[[ "$ENV" == "PREPROD" ]] || warn "NSC_ENV is '$ENV' (expected PREPROD). Continuing anyway."

ok "Starting PREPROD safety checks (APP_ROOT=$APP_ROOT, DATA_DIR=$DATA_DIR, NSC_ENV=$ENV)"

# 1) execution_plan exists + JSON valid + orders is array
need_file "$EXEC_PLAN_FILE"
json_valid "$EXEC_PLAN_FILE" || fail "execution_plan.json is not valid JSON"
ORDERS_TYPE="$(jq -r '(.orders // empty) | type' "$EXEC_PLAN_FILE" 2>/dev/null || true)"
[[ "$ORDERS_TYPE" == "array" ]] || fail "execution_plan.orders must be an array (found: ${ORDERS_TYPE:-missing})"
ORDERS_LEN="$(jq -r '.orders | length' "$EXEC_PLAN_FILE")"
ok "execution_plan.orders is an array (len=$ORDERS_LEN)"

# 2) kill_switch exists + JSON valid + hard_block invariant
need_file "$KILL_SWITCH_FILE"
json_valid "$KILL_SWITCH_FILE" || fail "kill_switch.json is not valid JSON"
HB="$(jq -r '.hard_block // false' "$KILL_SWITCH_FILE")"
[[ "$HB" == "true" || "$HB" == "false" ]] || fail "kill_switch.hard_block must be boolean"

if [[ "$HB" == "true" ]]; then
  [[ "$ORDERS_LEN" -eq 0 ]] || fail "Invariant violated: hard_block=true but orders_len=$ORDERS_LEN (must be 0)"
  ok "Invariant respected: hard_block=true => orders=0"
else
  ok "kill_switch.hard_block=false"
fi

# 3) open_positions valid JSON array (if file exists)
if [[ -f "$OPEN_POS_FILE" ]]; then
  json_valid "$OPEN_POS_FILE" || fail "open_positions.json is not valid JSON"
  OP_TYPE="$(jq -r 'type' "$OPEN_POS_FILE")"
  [[ "$OP_TYPE" == "array" ]] || fail "open_positions.json must be a JSON array (found: $OP_TYPE)"
  OP_LEN="$(jq -r 'length' "$OPEN_POS_FILE")"
  ok "open_positions.json valid array (len=$OP_LEN)"
else
  warn "open_positions.json missing (skipping array check)"
fi

# 4) simulated_fills prices non-null (if file exists)
if [[ -f "$SIM_FILLS_FILE" ]]; then
  json_valid "$SIM_FILLS_FILE" || fail "simulated_fills.json is not valid JSON"
  ROOT_TYPE="$(jq -r 'type' "$SIM_FILLS_FILE")"
  NULLS="0"; FILLS="0"

  if [[ "$ROOT_TYPE" == "array" ]]; then
    FILLS="$(jq -r 'length' "$SIM_FILLS_FILE")"
    NULLS="$(jq -r '[ .[] | select((.fill_price // .price // null) == null) ] | length' "$SIM_FILLS_FILE")"
  elif [[ "$ROOT_TYPE" == "object" ]]; then
    FT="$(jq -r '(.fills // empty) | type' "$SIM_FILLS_FILE" 2>/dev/null || true)"
    [[ "$FT" == "array" ]] || fail "simulated_fills.json must be array or contain object.fills as array"
    FILLS="$(jq -r '.fills | length' "$SIM_FILLS_FILE")"
    NULLS="$(jq -r '[ .fills[] | select((.fill_price // .price // null) == null) ] | length' "$SIM_FILLS_FILE")"
  else
    fail "simulated_fills.json must be array or object (found: $ROOT_TYPE)"
  fi

  [[ "$NULLS" -eq 0 ]] || fail "simulated_fills has null prices: $NULLS / $FILLS"
  ok "simulated_fills integrity OK (fills=$FILLS, null_prices=$NULLS)"
else
  warn "simulated_fills.json missing (skipping null-price check)"
fi

# 5) log scan (best-effort) for live execution traces
PATTERN='REAL_EXECUTION|EXECUTED_LIVE|placing (real|live) order|order sent|POST /api/v3/order|POST /fapi/v1/order|create_order\(|ccxt\.create_order'

FOUND=0
if [[ -d "$LOG_DIR" ]]; then
  if ls -1t "$LOG_DIR"/* >/dev/null 2>&1; then
    if grep -RqiE "$PATTERN" "$LOG_DIR"; then
      FOUND=1
      echo "❌ [SUSPICIOUS] live-execution traces found under $LOG_DIR" >&2
    fi
  fi
fi

if ls -1 /tmp/nsc_preprod_*.log >/dev/null 2>&1; then
  if grep -qiE "$PATTERN" /tmp/nsc_preprod_*.log; then
    FOUND=1
    echo "❌ [SUSPICIOUS] live-execution traces found in /tmp/nsc_preprod_*.log" >&2
  fi
fi

[[ "$FOUND" -eq 0 ]] || fail "Suspicious live-execution traces detected in logs."

ok "PREPROD safety checks passed."

