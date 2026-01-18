#!/usr/bin/env bash
set -euo pipefail

# =========================
# NSC PREPROD SAFETY CHECKS
# Institution-grade gate
# =========================

APP_DIR="${APP_DIR:-/opt/nsc/app}"
cd "$APP_DIR"

ENV="${NSC_ENV:-}"
if [ "$ENV" != "PREPROD" ]; then
  echo "❌ NSC_ENV must be PREPROD (got: ${ENV:-<empty>})"
  exit 1
fi

TELEMETRY_DIR="data/telemetry"
TRADING_DIR="data/trading"
LOG_DIR="${LOG_DIR:-data/telemetry}"  # fallback if you log there; adjust if you have /var/log/nsc/...
mkdir -p "$TELEMETRY_DIR"

fail() { echo "❌ $*"; exit 1; }
warn() { echo "⚠️  $*"; }
ok()   { echo "✅ $*"; }

# ---------- helpers ----------
json_get() {
  # json_get <file> <jq_expr>
  local f="$1"
  local expr="$2"
  [ -f "$f" ] || fail "missing file: $f"
  jq -r "$expr" "$f"
}

is_bool() {
  # returns 0 if value is true/false, else 1
  case "${1:-}" in
    true|false) return 0 ;;
    *) return 1 ;;
  esac
}

# ---------- 0) core files exist ----------
[ -f "$TRADING_DIR/open_positions.json" ] || fail "missing $TRADING_DIR/open_positions.json"
[ -f "$TRADING_DIR/execution_plan.json" ] || warn "missing $TRADING_DIR/execution_plan.json (ok if your flow writes a different plan path, but expected to exist)"

# ---------- 1) open_positions is valid JSON array ----------
jq -e 'type=="array"' "$TRADING_DIR/open_positions.json" >/dev/null || fail "open_positions.json must be a JSON array"
ok "open_positions.json is valid JSON array"

# ---------- 2) preprod_check can run and outputs telemetry ----------
# (This is the source-of-truth for many assertions)
if ! ./scripts/preprod_check.sh >/dev/null; then
  fail "preprod_check.sh failed"
fi
[ -f "$TELEMETRY_DIR/preprod_check.json" ] || fail "missing telemetry: $TELEMETRY_DIR/preprod_check.json"
ok "preprod_check executed and wrote telemetry"

PREPROD_OK="$(json_get "$TELEMETRY_DIR/preprod_check.json" '.ok // empty')"
[ "$PREPROD_OK" = "true" ] || fail "preprod_check.json ok != true"

# ---------- 3) DRY_RUN enforced markers ----------
# We use assertions emitted by preprod_check if available
DRY_ASSERT="$(jq -r '.assertions.dry_run_enforced // empty' "$TELEMETRY_DIR/preprod_check.json" 2>/dev/null || true)"
if [ -n "$DRY_ASSERT" ]; then
  [ "$DRY_ASSERT" = "true" ] || fail "dry_run_enforced assertion is not true"
  ok "dry_run_enforced assertion true"
else
  warn "dry_run_enforced assertion missing from preprod_check.json (consider adding it)"
fi

# ---------- 4) simulated_fills: no null price (if file exists) ----------
SIM_FILLS="$TRADING_DIR/simulated_fills.json"
if [ -f "$SIM_FILLS" ]; then
  # allow either array or object with fills
  null_count="$(jq -r '
    def prices:
      if type=="array" then .[]
      elif type=="object" and (.fills|type)=="array" then .fills[]
      else empty end;
    [prices | (.price // .fill_price // empty)] as $p
    | ( [prices | ((.price // .fill_price) == null)] | map(select(.==true)) | length )
  ' "$SIM_FILLS" 2>/dev/null || echo "ERR")"
  if [ "$null_count" = "ERR" ]; then
    fail "cannot parse simulated_fills.json"
  fi
  [ "$null_count" = "0" ] || fail "simulated_fills has null price/fill_price entries (count=$null_count)"
  ok "simulated_fills has no null prices"
else
  warn "no simulated_fills.json found (ok if your pipeline writes it elsewhere)"
fi

# ---------- 5) kill-switch invariant: hard_block => orders=0 ----------
KILL_FILE="$TRADING_DIR/kill_switch.json"
if [ -f "$KILL_FILE" ] && [ -f "$TRADING_DIR/execution_plan.json" ]; then
  hard_block="$(json_get "$KILL_FILE" '.hard_block // empty')"
  if [ -z "$hard_block" ]; then
    warn "kill_switch.json has no .hard_block"
  else
    is_bool "$hard_block" || fail "kill_switch.json .hard_block must be boolean true/false (got=$hard_block)"
    orders_len="$(json_get "$TRADING_DIR/execution_plan.json" '(.orders // []) | length')"
    if [ "$hard_block" = "true" ]; then
      [ "$orders_len" = "0" ] || fail "KILL-SWITCH VIOLATION: hard_block=true but execution_plan.orders.length=$orders_len"
      ok "hard_block=true => execution_plan.orders length is 0"
    else
      ok "hard_block=false (no invariant check on orders length)"
    fi
  fi
else
  warn "kill_switch.json or execution_plan.json missing (skip invariant hard_block=>orders=0)"
fi

# ---------- 6) open_positions immutability quick check (hash before/after loop) ----------
before_hash="$(sha256sum "$TRADING_DIR/open_positions.json" | awk '{print $1}')"
# run another preprod_check quickly
./scripts/preprod_check.sh >/dev/null || fail "preprod_check failed on 2nd run"
after_hash="$(sha256sum "$TRADING_DIR/open_positions.json" | awk '{print $1}')"
[ "$before_hash" = "$after_hash" ] || fail "open_positions mutated between runs (before=$before_hash after=$after_hash)"
ok "open_positions immutable across two runs"

# ---------- 7) Optional: total_notional visibility ----------
TOTAL_NOTIONAL="$(jq -r '
  .details.total_notional // .details.portfolio_total_notional // empty
' "$TELEMETRY_DIR/preprod_check.json" 2>/dev/null || true)"
if [ -n "$TOTAL_NOTIONAL" ] && [ "$TOTAL_NOTIONAL" != "null" ]; then
  ok "total_notional reported: $TOTAL_NOTIONAL"
else
  warn "total_notional not reported in telemetry (optional)"
fi

# ---------- 8) log scan: look for evidence of live execution ----------
# Adjust patterns to your actual logs.
# We scan recent telemetry logs if present + any preprod logs under /var/log/nsc if available.
PATTERN='(REAL EXECUTION|place_order_live|/api/v1/order|/api/v3/order|create_order|MARKET BUY|MARKET SELL|TRANSFER FUNDS|WITHDRAW)'
found=0

scan_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  if grep -E -n "$PATTERN" "$f" >/dev/null 2>&1; then
    echo "❌ suspicious live-execution pattern found in $f"
    grep -E -n "$PATTERN" "$f" | head -n 20
    found=1
  fi
}

# telemetry logs
for f in \
  "$TELEMETRY_DIR/preprod_daily.log" \
  "$TELEMETRY_DIR/preprod_weekly_stress.log" \
  "$TELEMETRY_DIR/preprod_weekly_scenarios.log"
do
  scan_file "$f"
done

# system logs (optional)
if [ -d /var/log/nsc ]; then
  while IFS= read -r f; do scan_file "$f"; done < <(find /var/log/nsc -maxdepth 3 -type f -name "*.log" 2>/dev/null | head -n 50)
fi

[ "$found" = "0" ] || fail "live-execution traces detected in logs (see above)"
ok "no live-execution traces detected (basic scan)"

ok "PREPROD safety checks passed."
