#!/usr/bin/env bash
set -euo pipefail

# Activer le venv
source /root/Bot_crypto_ultra/nsc-venv/bin/activate
export PYTHONPATH=/root/Bot_crypto_ultra/src

TOKEN="2d9624fb5808628625fa9cd4e500a5a86152bc794a66ef23"

echo "=== Smoke test legacy ==="

# 1) Check liveness
curl -sS http://127.0.0.1:8000/internal/__legacy_alive__ | jq .

# 2) Echo headers sans token
curl -sS http://127.0.0.1:8000/internal/__echo_headers__ | jq .

# 3) Echo headers avec token
curl -sS http://127.0.0.1:8000/internal/__echo_headers__ \
  -H "X-API-Token: $TOKEN" | jq .

# 4) CSV request via X-API-Token
# DISABLED LEGACY: curl -sS "http://127.0.0.1:8000/internal/ohlcv?symbol=ETHUSDT&tf=15m&days=1&format=csv" \
  -H "X-API-Token: $TOKEN" | head

# 5) JSON request via Bearer token
# DISABLED LEGACY: curl -sS "http://127.0.0.1:8000/internal/ohlcv?symbol=BTCUSDT&tf=1h&days=1&format=json" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0]'
