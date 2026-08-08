#!/usr/bin/env bash
set -u

echo "=========================================="
echo "NSC MACRO PREPROD DAILY CHECK"
echo "Obligations + Métaux précieux"
echo "=========================================="
date
echo

section() {
  echo
  echo "----- $1 -----"
}

file_age() {
  local f="$1"
  if [ -f "$f" ]; then
    local now ts
    now=$(date +%s)
    ts=$(stat -c %Y "$f" 2>/dev/null || echo 0)
    echo $((now - ts))
  else
    echo "NA"
  fi
}

BONDS_SIGNAL="/opt/nsc/app/src/v2/data/bonds/bond_signal.json"
BONDS_INPUT="/opt/nsc/app/src/v2/data/portfolio/inputs/bonds_portfolio_input.json"
METALS_SIGNAL="/opt/nsc/app/src/v2/data/precious_metals/metals_signal.json"
METALS_INPUT="/opt/nsc/app/src/v2/data/portfolio/inputs/precious_metals_portfolio_input.json"
PORTFOLIO_TARGET="/opt/nsc/data/preprod/portfolio/portfolio_target.json"
NSC_LOG="/opt/nsc/app/src/v2/logs/nsc.log"

section "API HEALTH"
curl -s http://127.0.0.1:8000/health 2>/dev/null || echo "health endpoint indisponible"

section "SYSTEMD - OBLIGATIONS"
systemctl status nsc-bonds-preprod.timer --no-pager -l 2>/dev/null || true
echo
systemctl status nsc-bonds-preprod.service --no-pager -l 2>/dev/null || true

section "SYSTEMD - METAUX PRECIEUX"
systemctl status nsc-precious-metals-preprod.timer --no-pager -l 2>/dev/null || true
echo
systemctl status nsc-precious-metals-preprod.service --no-pager -l 2>/dev/null || true

section "SIGNAL - OBLIGATIONS"
if [ -f "$BONDS_SIGNAL" ]; then
  echo "file=$BONDS_SIGNAL"
  echo "age_sec=$(file_age "$BONDS_SIGNAL")"
  jq '{
    brick,
    regime,
    bond_macro_score,
    target_exposure,
    duration_target,
    confidence,
    allocation,
    drivers,
    risk_flags,
    execution_mode,
    timestamp
  }' "$BONDS_SIGNAL"
else
  echo "Signal Obligations introuvable"
fi

section "PORTFOLIO INPUT - OBLIGATIONS"
if [ -f "$BONDS_INPUT" ]; then
  echo "file=$BONDS_INPUT"
  echo "age_sec=$(file_age "$BONDS_INPUT")"
  jq '.' "$BONDS_INPUT"
else
  echo "Portfolio input Obligations introuvable"
fi

section "SIGNAL - METAUX PRECIEUX"
if [ -f "$METALS_SIGNAL" ]; then
  echo "file=$METALS_SIGNAL"
  echo "age_sec=$(file_age "$METALS_SIGNAL")"
  jq '{
    brick,
    regime,
    metals_macro_score,
    target_exposure,
    confidence,
    allocation,
    drivers,
    risk_flags,
    inertia_profile,
    execution_mode,
    timestamp
  }' "$METALS_SIGNAL"
else
  echo "Signal Métaux précieux introuvable"
fi

section "PORTFOLIO INPUT - METAUX PRECIEUX"
if [ -f "$METALS_INPUT" ]; then
  echo "file=$METALS_INPUT"
  echo "age_sec=$(file_age "$METALS_INPUT")"
  jq '.' "$METALS_INPUT"
else
  echo "Portfolio input Métaux précieux introuvable"
fi

section "PORTFOLIO TARGET INTEGRATION"
if [ -f "$PORTFOLIO_TARGET" ]; then
  echo "file=$PORTFOLIO_TARGET"
  echo "age_sec=$(file_age "$PORTFOLIO_TARGET")"
  jq '{
    engine,
    portfolio_regime,
    final_brick_weights,
    brick_confidence,
    brick_regimes,
    brick_roles,
    brick_allocations,
    timestamp
  }' "$PORTFOLIO_TARGET"
else
  echo "portfolio_target introuvable"
fi

section "JOURNALCTL - OBLIGATIONS"
journalctl -u nsc-bonds-preprod.service -n 30 --no-pager 2>/dev/null || true

section "JOURNALCTL - METAUX PRECIEUX"
journalctl -u nsc-precious-metals-preprod.service -n 30 --no-pager 2>/dev/null || true

section "NSC LOG - OBLIGATIONS"
grep -Ei 'bonds_pipeline|bond_signal_engine' "$NSC_LOG" | tail -n 20 2>/dev/null || echo "Aucune trace bonds_pipeline"

section "NSC LOG - METAUX PRECIEUX"
grep -Ei 'precious_metals_pipeline|metals_signal_engine' "$NSC_LOG" | tail -n 20 2>/dev/null || echo "Aucune trace precious_metals_pipeline"

section "SANITY CHECKS"
FAIL=0

if [ -f "$BONDS_SIGNAL" ]; then
  echo "[OK] Signal Obligations présent"
else
  echo "[KO] Signal Obligations absent"
  FAIL=1
fi

if [ -f "$BONDS_INPUT" ]; then
  echo "[OK] Portfolio input Obligations présent"
else
  echo "[KO] Portfolio input Obligations absent"
  FAIL=1
fi

if [ -f "$METALS_SIGNAL" ]; then
  echo "[OK] Signal Métaux précieux présent"
else
  echo "[KO] Signal Métaux précieux absent"
  FAIL=1
fi

if [ -f "$METALS_INPUT" ]; then
  echo "[OK] Portfolio input Métaux précieux présent"
else
  echo "[KO] Portfolio input Métaux précieux absent"
  FAIL=1
fi

if [ -f "$PORTFOLIO_TARGET" ]; then
  echo "[OK] portfolio_target présent"
else
  echo "[WARN] portfolio_target absent"
fi

section "DIAGNOSTIC METIER"
if [ -f "$BONDS_SIGNAL" ]; then
  echo "Obligations :"
  jq -r '"  - regime=\(.regime)\n  - target_exposure=\(.target_exposure)\n  - confidence=\(.confidence)\n  - duration_target=\(.duration_target)\n  - rate_signal=\(.drivers.rate_signal)\n  - inflation_signal=\(.drivers.inflation_signal)\n  - credit_signal=\(.drivers.credit_signal)\n  - bond_vol_signal=\(.drivers.bond_vol_signal)"' "$BONDS_SIGNAL"
fi

echo

if [ -f "$METALS_SIGNAL" ]; then
  echo "Métaux précieux :"
  jq -r '"  - regime=\(.regime)\n  - target_exposure=\(.target_exposure)\n  - confidence=\(.confidence)\n  - inflation_signal=\(.drivers.inflation_signal)\n  - real_rate_signal=\(.drivers.real_rate_signal)\n  - systemic_stress_signal=\(.drivers.systemic_stress_signal)\n  - usd_signal=\(.drivers.usd_signal)"' "$METALS_SIGNAL"
fi

section "FINAL STATUS"
if [ "$FAIL" -eq 0 ]; then
  echo "GLOBAL STATUS: OK"
  echo "Conclusion: préprod macro autonome opérationnelle."
else
  echo "GLOBAL STATUS: CHECK REQUIRED"
  echo "Conclusion: corriger les éléments KO."
fi
