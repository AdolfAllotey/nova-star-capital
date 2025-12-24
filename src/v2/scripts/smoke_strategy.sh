#!/usr/bin/env bash
set -euo pipefail

# ================== Config (surchageable via env) ==================
PROJECT_ROOT="${PROJECT_ROOT:-/root/Bot_crypto_ultra}"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/nsc-venv}"
PYTHONPATH_DIR="${PYTHONPATH_DIR:-$PROJECT_ROOT/src}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-$BASE_URL/health}"
RETRIES="${RETRIES:-40}"
SLEEP_SECS="${SLEEP_SECS:-0.5}"

SYMBOLS_CSV="${SYMBOLS_CSV:-BTCUSDT,ETHUSDT,SOLUSDT}"
N_TOP="${N_TOP:-3}"
TF="${TF:-1h}"
LOOKBACK="${LOOKBACK:-96}"
BUDGET="${BUDGET:-5000}"

# ================== Helpers ==================
log(){ echo -e "==> $*"; }
warn(){ echo -e "⚠️  $*" >&2; }
die(){ echo -e "❌ $*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "Outil requis manquant: $1"; }

curl_json() {
  curl -sS --fail --max-time 5 "$@" || return 1
}

wait_health() {
  log "Health"
  for ((i=1; i<=RETRIES; i++)); do
    if curl -sS --fail --max-time 2 "$HEALTH_ENDPOINT" >/dev/null; then
      curl -sS "$HEALTH_ENDPOINT" | jq .
      return 0
    fi
    sleep "$SLEEP_SECS"
  done
  return 1
}

# ================== Pré-checks ==================
need jq
need curl
[[ -d "$VENV_DIR" ]] || warn "Venv introuvable: $VENV_DIR (je continue si python/jq/curl sont globaux)"

# Optionnel: activer le venv si dispo
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  log "Activation du venv"
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate" || warn "Activation venv échouée, je continue..."
  export PYTHONPATH="$PYTHONPATH_DIR"
fi

if ! wait_health; then
  die "API indisponible (health KO)"
fi

log "/api/strategy/_status"
curl_json "$BASE_URL/api/strategy/_status" | jq .

log "/top (mock=1)"
curl_json "$BASE_URL/api/strategy/top?symbols=$SYMBOLS_CSV&tf=$TF&lookback=$LOOKBACK&n=$N_TOP&mock=1" | jq .

log "/allocations (mock=1)"
curl_json "$BASE_URL/api/strategy/allocations?$(echo "$SYMBOLS_CSV" | awk -F, '{for(i=1;i<=NF;i++) printf "symbols=%s&",$i}')budget=$BUDGET&tf=$TF&lookback=$LOOKBACK&mock=1" | jq .

log "/top (mock=0) – données réelles"
if ! curl_json "$BASE_URL/api/strategy/top?symbols=$SYMBOLS_CSV&tf=$TF&lookback=$LOOKBACK&n=$N_TOP&mock=0"; then
  warn "Échec /top (mock=0) — probable backend OHLCV indisponible"
else
  curl -sS "$BASE_URL/api/strategy/top?symbols=$SYMBOLS_CSV&tf=$TF&lookback=$LOOKBACK&n=$N_TOP&mock=0" | jq .
fi

log "/allocations (mock=0) – données réelles"
if ! curl_json "$BASE_URL/api/strategy/allocations?$(echo "$SYMBOLS_CSV" | awk -F, '{for(i=1;i<=NF;i++) printf "symbols=%s&",$i}')budget=$BUDGET&tf=$TF&lookback=$LOOKBACK&mock=0"; then
  warn "Échec /allocations (mock=0) — probable backend OHLCV indisponible"
else
  curl -sS "$BASE_URL/api/strategy/allocations?$(echo "$SYMBOLS_CSV" | awk -F, '{for(i=1;i<=NF;i++) printf "symbols=%s&",$i}')budget=$BUDGET&tf=$TF&lookback=$LOOKBACK&mock=0" | jq .
fi

log "Tests terminés ✅"
