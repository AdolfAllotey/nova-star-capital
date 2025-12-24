#!/usr/bin/env bash
set -euo pipefail

### --- Paramètres ---
APP_DIR="/root/Bot_crypto_ultra"
SRC_DIR="$APP_DIR/src"
VENV_DIR="$APP_DIR/nsc-venv"
SERVICE="nsc-api.service"
API_BASE="http://127.0.0.1:8000"
HEALTH="$API_BASE/health"

# Exemples de requêtes
STATUS="$API_BASE/api/strategy/_status"
TOP="$API_BASE/api/strategy/top?symbols=BTCUSDT,ETHUSDT,SOLUSDT&tf=1h&lookback=96&n=3&mock=1"
ALLOC="$API_BASE/api/strategy/allocations?symbols=BTCUSDT&symbols=ETHUSDT&symbols=SOLUSDT&budget=5000&tf=1h&lookback=96&mock=1"

echo "==> Activation venv"
source "$VENV_DIR/bin/activate"

echo "==> Export PYTHONPATH"
export PYTHONPATH="$SRC_DIR"

echo "==> Compilation (py_compile)"
python -m py_compile \
  "$SRC_DIR/v2/api/server.py" \
  "$SRC_DIR/v2/api/strategy.py"

echo "==> Restart service: $SERVICE"
sudo systemctl restart "$SERVICE"

echo "==> Attente de l'API ($HEALTH)"
for i in $(seq 1 40); do
  if curl -fsS "$HEALTH" >/dev/null; then
    echo "API up ✅"
    break
  fi
  sleep 0.5
  if [[ $i -eq 40 ]]; then
    echo "❌ API KO (health check échoué)"; exit 1
  fi
done

echo "==> Routes /api/strategy/* présentes ?"
curl -fsS "$API_BASE/openapi.json" \
 | jq -r '.paths|keys[]' \
 | sort \
 | grep '^/api/strategy' || {
   echo "❌ Les routes /api/strategy n'apparaissent pas dans OpenAPI"; exit 1; }

echo "==> /_status"
curl -fsS "$STATUS" | jq .

echo "==> /top (mock=1 pour test rapide, ne dépend pas des données OHLCV)"
curl -fsS "$TOP" | jq .

echo "==> /allocations (mock=1)"
curl -fsS "$ALLOC" | jq .

echo "==> Smoke tests OK ✅"
