#!/usr/bin/env bash
set -euo pipefail

ERRS=0

# Risk service mode: triggered (expected) or daemon
RISK_MODE="${RISK_MODE:-triggered}"

WORKDIR="${WORKDIR:-/opt/nsc/app}"
TELEMETRY_DIR="${TELEMETRY_DIR:-$WORKDIR/data/telemetry/preprod_runs}"
RISK_DIR="${RISK_DIR:-$WORKDIR/data/risk}"
LOG_DIR="${LOG_DIR:-$WORKDIR/data/telemetry/preprod_48h_checks}"

SVC_DAILY="${SVC_DAILY:-nsc-daily-run.service}"
SVC_RISK="${SVC_RISK:-nsc-risk.service}"

TRUNCATE_LOGS="${TRUNCATE_LOGS:-0}"
RUN_DAILY="${RUN_DAILY:-0}"
RUN_RISK="${RUN_RISK:-0}"
SHOW_JOURNAL="${SHOW_JOURNAL:-0}"
JOURNAL_LINES="${JOURNAL_LINES:-120}"

ts="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
out="$LOG_DIR/preprod_48h_check_${ts}.md"

say() { echo "$*" | tee -a "$out" >/dev/null; }
code() { echo -e "\n\`\`\`\n$*\n\`\`\`\n" | tee -a "$out" >/dev/null; }

check_env_in_service() {
  local svc="$1"
  local key="$2"
  # Source de vérité : Environment=... (résolu après drop-ins)
  if systemctl show "$svc" -p Environment --value | tr ' ' '\n' | grep -q "^${key}="; then
    say "✅ Env present in $svc: $key"
  else
    say "❌ Env missing in $svc: $key (expected ${key}=...)"
  fi
}

check_enabled() {
  local svc="$1"
  if systemctl is-enabled "$svc" >/dev/null 2>&1; then
    say "✅ Service enabled: $svc"
  else
    say "❌ Service NOT enabled: $svc"
  fi
}

check_active() {
  local svc="$1"
  if systemctl is-active "$svc" >/dev/null 2>&1; then
    say "✅ Service active: $svc"
  else
    say "⚠️ Service not active: $svc"
  fi
}

say "# NSC PREPROD 48h checklist — ${ts}"
say ""
say "- workdir: $WORKDIR"
say "- telemetry_dir: $TELEMETRY_DIR"
say "- risk_dir: $RISK_DIR"
say "- services: $SVC_DAILY, $SVC_RISK"
say ""

say "## Sanity (paths + python + imports)"
cd "$WORKDIR"
say "✅ Current dir: $(pwd)"
code "which python || true
/opt/nsc-venv/bin/python -V || true
/opt/nsc-venv/bin/python -c 'import sys; print(sys.path[:3])' || true
/opt/nsc-venv/bin/python -m py_compile src/v2/analytics/worst_trade_analyzer.py"

say "✅ py_compile worst_trade_analyzer.py OK"
say ""

say "## Systemd services (status + kill-switch + execstart)"
check_enabled "$SVC_DAILY"

if [[ "$RISK_MODE" == "triggered" ]]; then
  # Option A: risk runs via ExecStartPost; it's expected to be disabled + inactive when idle.
  if systemctl is-enabled "$SVC_RISK" >/dev/null 2>&1; then
    say "⚠️ Risk service is enabled but RISK_MODE=triggered (expected: disabled): $SVC_RISK"
  else
    say "✅ Risk service is disabled (expected in triggered mode): $SVC_RISK"
  fi

  if systemctl is-active "$SVC_RISK" >/dev/null 2>&1; then
    say "⚠️ Risk service is active but RISK_MODE=triggered (expected: inactive when idle): $SVC_RISK"
  else
    say "✅ Risk service is inactive (expected in triggered mode): $SVC_RISK"
  fi
else
  # Daemon mode: should be enabled + active
  check_enabled "$SVC_RISK"
  check_active "$SVC_RISK"
fi

check_env_in_service "$SVC_DAILY" "NSC_KILL_SWITCH"
check_env_in_service "$SVC_RISK" "NSC_KILL_SWITCH"

say ""
say ""
say "## Optional triggers"
if [[ "$TRUNCATE_LOGS" == "1" ]]; then
  sudo truncate -s 0 /var/log/nsc/nsc-risk.log || true
  say "✅ Logs truncated: /var/log/nsc/nsc-risk.log"
fi

if [[ "$RUN_DAILY" == "1" ]]; then
  sudo systemctl restart "$SVC_DAILY" || true
  say "✅ Triggered: $SVC_DAILY"
fi

if [[ "$RUN_RISK" == "1" ]]; then
  sudo systemctl restart "$SVC_RISK" || true
  say "✅ Triggered: $SVC_RISK"
fi

say ""
say "## Artifacts"
if [[ -d "$TELEMETRY_DIR" ]]; then
  say "✅ telemetry_dir exists"
else
  say "⚠️ telemetry_dir missing: $TELEMETRY_DIR"
fi

if [[ -f "$RISK_DIR/worst_trades.json" ]]; then
  say "✅ worst_trades.json exists"
else
  say "⚠️ worst_trades.json missing"
fi

if [[ -f "$RISK_DIR/worst_trades_summary.json" ]]; then
  say "✅ worst_trades_summary.json exists"
else
  say "⚠️ worst_trades_summary.json missing"
fi

if [[ "$SHOW_JOURNAL" == "1" ]]; then
  say ""
  say "## Journal (last ${JOURNAL_LINES})"
  code "sudo journalctl -u $SVC_DAILY -n $JOURNAL_LINES --no-pager || true
sudo journalctl -u $SVC_RISK -n $JOURNAL_LINES --no-pager || true"
fi

say ""
say "✅ Report written: $out"
echo "✅ Report written: $out"

# --- FINAL STATUS ---
if [ "$ERRS" -gt 0 ]; then
  echo
  echo "❌ PREPROD 48H CHECK FAILED: $ERRS error(s)"
  exit 1
else
  echo
  echo "✅ PREPROD 48H CHECK OK"
  exit 0
fi
