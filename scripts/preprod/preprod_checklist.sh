#!/usr/bin/env bash
set -u

APP_DIR="/opt/nsc/app"
DATA_DIR="$APP_DIR/data"
ANALYSIS_DIR="$DATA_DIR/analysis"
TRADING_DIR="$DATA_DIR/trading"
LOG_DIR="$APP_DIR/src/v2/logs"
LOG_FILE="$LOG_DIR/nsc.log"

TS() { date -Iseconds; }
hr() { echo "------------------------------------------------------------"; }
info(){ echo "ℹ️  $*"; }
ok(){ echo "✅ $*"; }
warn(){ echo "⚠️  $*"; }
die(){ echo "❌ $*"; exit 1; }

# Non-fatal runner (collect warnings, never stops the whole script)
run() { bash -lc "$*" >/dev/null 2>&1 || true; }

jq_get_plan() {
  jq -r '{
    run_id:.run_id,
    status:.status,
    writer:.writer,
    orders:(.orders|length),
    note:(.note // ""),
    hard_block:((.governance.hard_block // false) | tostring),
    mode:(.governance.mode // ""),
    reasons:((.governance.reasons // []) | join(";"))
  } | "run_id=\(.run_id) status=\(.status) writer=\(.writer) orders=\(.orders) hard_block=\(.hard_block) note=\(.note)"' \
  "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "NO_EXECUTION_PLAN"
}

plan_json_compact() {
  jq -c '{run_id,status,writer,orders:(.orders|length),note:(.note // "")}' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "{}"
}

cleanup_plan() {
  rm -f "$TRADING_DIR/execution_plan.json" 2>/dev/null || true
}

backup_file() {
  local f="$1"
  if [ -f "$f" ]; then
    cp -f "$f" "$f.bak_checklist" 2>/dev/null || true
  fi
}

restore_file() {
  local f="$1"
  if [ -f "$f.bak_checklist" ]; then
    mv -f "$f.bak_checklist" "$f" 2>/dev/null || true
  fi
}

inject_vol_shock() {
  # keep existing file
  backup_file "$ANALYSIS_DIR/volatility_state_machine_pro.json"
  cat > "$ANALYSIS_DIR/volatility_state_machine_pro.json" <<'JSON'
{"regime":"shock","flag":"vol_shock","score":0,"severity":"critical","reasons":["test_injection"],"timestamp":"2025-12-29T00:00:00Z"}
JSON
}

uninject_vol_shock() {
  restore_file "$ANALYSIS_DIR/volatility_state_machine_pro.json"
}

# Ensure script uses fresh run_id unless explicitly manual+keep
gen_manual_run_id() {
  export NSC_KEEP_RUN_ID=1
  export NSC_RUN_ID="manual-$(date +%s)"
}

unset_manual_run_id() {
  unset NSC_RUN_ID || true
  unset NSC_KEEP_RUN_ID || true
}

# Optional section switch
# NSC_PREPROD_OPTIONAL=1 enables extra checks + mini stress loop
OPTIONAL="${NSC_PREPROD_OPTIONAL:-0}"

echo "ℹ️  NSC PREPROD CHECKLIST — $(TS)"
hr

# PRE-FLIGHT: ensure dirs exist
[ -d "$APP_DIR" ] || die "APP_DIR missing: $APP_DIR"
[ -d "$DATA_DIR" ] || die "DATA_DIR missing: $DATA_DIR"
[ -d "$TRADING_DIR" ] || die "TRADING_DIR missing: $TRADING_DIR"

# --------------------------
# CHECK 1 — Normal run (clean state): coherent plan expected
# --------------------------
info "CHECK 1 — Normal run (clean state): expect status=ok, orders>0, writer=execution_engine_pro"
cleanup_plan
unset_manual_run_id
run "cd $APP_DIR && NSC_ENV=PREPROD python -m src.v2.trading.trading_kernel"
echo "plan: $(jq_get_plan)"

# Soft assertions: we don't hard fail here, just warnings
STATUS="$(jq -r '.status // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
WRITER="$(jq -r '.writer // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
ORDERS="$(jq -r '(.orders|length) // 0' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "0")"

if [ "$STATUS" != "ok" ]; then warn "expected status=ok, got $STATUS"; else ok "status=ok"; fi
if [ "$WRITER" != "execution_engine_pro" ]; then warn "expected writer=execution_engine_pro, got $WRITER"; else ok "writer=execution_engine_pro"; fi
if [ "${ORDERS:-0}" -le 0 ]; then warn "expected orders>0, got ${ORDERS:-0}"; else ok "orders>0"; fi
hr

# --------------------------
# CHECK 2 — Hard-block injection (vol shock): expect status=blocked, writer=trading_kernel, hard_block=true
# --------------------------
info "CHECK 2 — Hard-block injection: expect status=blocked, orders=0, writer=trading_kernel, governance.hard_block=true"
cleanup_plan
gen_manual_run_id
inject_vol_shock

run "cd $APP_DIR && NSC_ENV=PREPROD NSC_SKIP_VOLATILITY_STATE_MACHINE_PRO=1 python -m src.v2.trading.trading_kernel"

echo "plan: $(jq_get_plan)"

STATUS="$(jq -r '.status // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
WRITER="$(jq -r '.writer // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
ORDERS="$(jq -r '(.orders|length) // 0' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "0")"
HB="$(jq -r '(.governance.hard_block // false) | tostring' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "false")"

if [ "$STATUS" = "blocked" ]; then ok "status=blocked"; else warn "expected status=blocked, got $STATUS"; fi
if [ "$WRITER" = "trading_kernel" ]; then ok "writer=trading_kernel"; else warn "expected writer=trading_kernel, got $WRITER"; fi
if [ "${ORDERS:-0}" -eq 0 ]; then ok "orders=0"; else warn "expected orders=0, got ${ORDERS:-0}"; fi
if [ "$HB" = "true" ]; then ok "governance.hard_block=true"; else warn "expected hard_block=true, got $HB"; fi
hr

# --------------------------
# CHECK 3 — Idempotence: re-run execution_engine_pro only, plan must remain unchanged
# --------------------------
info "CHECK 3 — Re-run execution_engine_pro ONLY after hard-block: plan must remain unchanged"
BEFORE="$(plan_json_compact)"
run "cd $APP_DIR && NSC_ENV=PREPROD python -m src.v2.analysis.execution_engine_pro"
AFTER="$(plan_json_compact)"

echo "before: $BEFORE"
echo "after : $AFTER"

if [ "$BEFORE" = "$AFTER" ]; then
  ok "idempotence OK (execution_engine_pro did not override hard-block plan)"
else
  warn "plan mutated (idempotence failed or env not clean)"
fi

# verify log evidence (best-effort)
if [ -f "$LOG_FILE" ]; then
  if rg -n "HARD_BLOCK\]\[IDEMPOTENCE\] preserving trading_kernel hard-block plan" "$LOG_FILE" >/dev/null 2>&1; then
    ok "log shows idempotence preservation (HARD_BLOCK][IDEMPOTENCE])"
  else
    warn "no idempotence preservation log found (may be normal if log rotated)"
  fi
else
  warn "log file not found: $LOG_FILE"
fi
hr

# restore injection
uninject_vol_shock
unset_manual_run_id

# --------------------------
# CHECK 4 — run_id behavior (fresh per run; manual respected)
# --------------------------
info "CHECK 4 — run_id behavior"
cleanup_plan
unset_manual_run_id
run "cd $APP_DIR && NSC_ENV=PREPROD python -m src.v2.trading.trading_kernel"
R1="$(jq -r '.run_id // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"

cleanup_plan
unset_manual_run_id
run "cd $APP_DIR && NSC_ENV=PREPROD python -m src.v2.trading.trading_kernel"
R2="$(jq -r '.run_id // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"

echo "run_id no-keep: r1=$R1 r2=$R2"
if [ -n "$R1" ] && [ -n "$R2" ] && [ "$R1" != "$R2" ]; then
  ok "run_id changes between runs (expected)"
else
  warn "run_id did not change (unexpected) — check run_id propagation block"
fi

# Manual run_id respected (plan + ledger)
cleanup_plan
gen_manual_run_id
run "cd $APP_DIR && NSC_ENV=PREPROD python -m src.v2.trading.trading_kernel"

RID_PLAN="$(jq -r '.run_id // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
RID_LEDGER="$(tail -n 1 "$TRADING_DIR/execution_decisions.jsonl" 2>/dev/null | jq -r '.run_id // ""' 2>/dev/null || echo "")"
echo "manual: ENV=$NSC_RUN_ID plan=$RID_PLAN ledger_last=$RID_LEDGER"

if [ "$RID_PLAN" = "$NSC_RUN_ID" ]; then ok "plan respects manual run_id"; else warn "plan does NOT respect manual run_id"; fi
if rg -F "$NSC_RUN_ID" "$TRADING_DIR/execution_decisions.jsonl" >/dev/null 2>&1; then ok "ledger contains run_id"; else warn "ledger missing manual run_id"; fi
hr

# --------------------------
# OPTIONAL — Extra checks + mini stress (opt-in)
# --------------------------
if [ "$OPTIONAL" = "1" ]; then
  info "OPTIONAL — Extra checks enabled (NSC_PREPROD_OPTIONAL=1)"
  hr

  # Optional A: verify core analysis outputs exist
  info "OPTIONAL A — Verify key analysis outputs exist"
  for f in \
    "$ANALYSIS_DIR/momentum_scores.json" \
    "$ANALYSIS_DIR/signal_votes.json" \
    "$ANALYSIS_DIR/market_regime_detector.json" \
    "$ANALYSIS_DIR/correlation_regime_engine_pro.json" \
    "$ANALYSIS_DIR/risk_engine_pro.json"
  do
    if [ -f "$f" ]; then ok "exists: $(basename "$f")"; else warn "missing: $(basename "$f")"; fi
  done
  hr

  # Optional B: event bus contains correlation state (best-effort)
  info "OPTIONAL B — Event bus contains correlation.regime.state (best-effort)"
  EV="$DATA_DIR/telemetry/event_bus.jsonl"
  if [ -f "$EV" ]; then
    if rg -F '"type":"correlation.regime.state"' "$EV" >/dev/null 2>&1; then
      ok "found correlation.regime.state in event bus"
    else
      warn "no correlation.regime.state in event bus"
    fi
  else
    warn "event bus file missing: $EV"
  fi
  hr

  # Optional C: stale plan guard sanity (ensure we start clean)
  info "OPTIONAL C — Ensure stale execution_plan guard won't block clean runs"
  cleanup_plan
  unset_manual_run_id
  run "cd $APP_DIR && NSC_ENV=PREPROD python -m src.v2.analysis.execution_engine_pro"
  STATUS="$(jq -r '.status // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
  NOTE="$(jq -r '.note // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
  echo "plan: $(jq_get_plan)"
  if [ "$STATUS" = "blocked" ] && [ "$NOTE" = "blocked_stale_execution_plan_file_guard" ]; then
    warn "still blocked by stale file guard after cleanup — indicates write path or cleanup mismatch"
  else
    ok "stale guard not blocking clean engine-only run (expected)"
  fi
  hr

  # Optional D: mini stress loop (N runs) — validates no unexpected hard crash + run_id uniqueness
  info "OPTIONAL D — Mini stress loop (default N=10). Set NSC_PREPROD_STRESS_N to change."
  N="${NSC_PREPROD_STRESS_N:-10}"
  ok_count=0
  blocked_count=0
  last_rid=""
  uniq_ok=1

  for i in $(seq 1 "$N"); do
    cleanup_plan
    unset_manual_run_id
    run "cd $APP_DIR && NSC_ENV=PREPROD python -m src.v2.trading.trading_kernel"

    rid="$(jq -r '.run_id // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"
    st="$(jq -r '.status // ""' "$TRADING_DIR/execution_plan.json" 2>/dev/null || echo "")"

    if [ "$st" = "ok" ]; then ok_count=$((ok_count+1)); else blocked_count=$((blocked_count+1)); fi
    if [ -n "$last_rid" ] && [ -n "$rid" ] && [ "$rid" = "$last_rid" ]; then uniq_ok=0; fi
    last_rid="$rid"
  done

  echo "stress: N=$N ok=$ok_count blocked=$blocked_count"
  if [ "$uniq_ok" = "1" ]; then ok "run_id changed across iterations"; else warn "run_id repeated across iterations"; fi
  hr
fi

ok "Checklist completed."
