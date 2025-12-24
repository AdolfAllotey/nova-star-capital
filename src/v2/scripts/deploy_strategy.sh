#!/usr/bin/env bash
set -euo pipefail

# ================== Config (surchargeable via env) ==================
PROJECT_ROOT="${PROJECT_ROOT:-/root/Bot_crypto_ultra}"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/nsc-venv}"
PYTHONPATH_DIR="${PYTHONPATH_DIR:-$PROJECT_ROOT/src}"
SERVICE="${SERVICE:-nsc-api.service}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-$BASE_URL/health}"
RETRIES="${RETRIES:-40}"         # 40 tentatives * 0.5s = 20s
SLEEP_SECS="${SLEEP_SECS:-0.5}"  # attente entre tentatives
SYMBOLS_CSV="${SYMBOLS_CSV:-BTCUSDT,ETHUSDT,SOLUSDT}"
N_TOP="${N_TOP:-3}"
TF="${TF:-1h}"
LOOKBACK="${LOOKBACK:-96}"

SERVER_PY="$PYTHONPATH_DIR/v2/api/server.py"
STRATEGY_PY="$PYTHONPATH_DIR/v2/api/strategy.py"

# ================== Helpers ==================
log(){ echo -e "==> $*"; }
die(){ echo -e "❌ $*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "Outil requis manquant: $1"; }

curl_json() {
  curl -sS --fail --max-time 5 "$@" || return 1
}

wait_health() {
  log "Attente de l'API ($HEALTH_ENDPOINT)"
  for ((i=1; i<=RETRIES; i++)); do
    if curl -sS --fail --max-time 2 "$HEALTH_ENDPOINT" >/dev/null; then
      echo "API up ✅"
      return 0
    fi
    sleep "$SLEEP_SECS"
  done
  return 1
}

require_files() {
  [[ -f "$SERVER_PY" ]]   || die "Introuvable: $SERVER_PY"
  [[ -f "$STRATEGY_PY" ]] || die "Introuvable: $STRATEGY_PY"
}

# ================== Pré-checks ==================
need jq
need systemctl
need python
need curl
require_files

[[ -d "$VENV_DIR" ]] || die "Venv introuvable: $VENV_DIR"

log "Racine projet :  $PROJECT_ROOT"
log "Virtualenv     : $VENV_DIR"
log "Activation du venv"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate" || die "Impossible d'activer le venv: $VENV_DIR"

log "Export PYTHONPATH"
export PYTHONPATH="$PYTHONPATH_DIR"

log "Compilation des modules"
python -m py_compile "$SERVER_PY" "$STRATEGY_PY"

log "Redémarrage du service systemd : $SERVICE"
systemctl restart "$SERVICE"

if ! wait_health; then
  journalctl -u "$SERVICE" -n 80 --no-pager -o cat >&2 || true
  die "API indisponible après redémarrage (health KO)"
fi

log "Vérification des routes /api/strategy/*"
paths=$(curl_json "$BASE_URL/openapi.json" | jq -r '.paths|keys[]' | sort || true)
echo "$paths" | grep '^/api/strategy' || die "Routes /api/strategy absentes de l'OpenAPI"
echo "$paths" | grep '^/api/strategy' | sed 's/^/  /g'

log "Test /_status"
curl_json "$BASE_URL/api/strategy/_status" | jq .

log "Test /top (mock=1, rapide)"
curl_json "$BASE_URL/api/strategy/top?symbols=$SYMBOLS_CSV&tf=$TF&lookback=$LOOKBACK&n=$N_TOP&mock=1" | jq .

log "Test /allocations (mock=1)"
curl_json "$BASE_URL/api/strategy/allocations?$(echo "$SYMBOLS_CSV" | awk -F, '{for(i=1;i<=NF;i++) printf "symbols=%s&",$i}')budget=5000&tf=$TF&lookback=$LOOKBACK&mock=1" | jq .

log "Déploiement terminé ✅"
