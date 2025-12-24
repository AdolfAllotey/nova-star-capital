#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"

echo "==> Health"
curl -fsS "$API_BASE/health" | jq .

echo "==> /api/strategy/_status"
curl -fsS "$API_BASE/api/strategy/_status" | jq .

echo "==> /top (mock=1)"
curl -fsS "$API_BASE/api/strategy/top?symbols=BTCUSDT,ETHUSDT,SOLUSDT&tf=1h&lookback=96&n=3&mock=1" | jq .

echo "==> /allocations (mock=1)"
curl -fsS "$API_BASE/api/strategy/allocations?symbols=BTCUSDT&symbols=ETHUSDT&symbols=SOLUSDT&budget=5000&tf=1h&lookback=96&mock=1" | jq .

# Essai “réel” (mock=0) — dépend de ton endpoint OHLCV interne
echo "==> /top (mock=0) - peut échouer si OHLCV n'est pas prêt"
set +e
curl -fsS "$API_BASE/api/strategy/top?symbols=BTCUSDT,ETHUSDT,SOLUSDT&tf=1h&lookback=96&n=3&mock=0" | jq .
RET1=$?
set -e

echo "==> /allocations (mock=0) - peut échouer si OHLCV n'est pas prêt"
set +e
curl -fsS "$API_BASE/api/strategy/allocations?symbols=BTCUSDT&symbols=ETHUSDT&symbols=SOLUSDT&budget=5000&tf=1h&lookback=96&mock=0" | jq .
RET2=$?
set -e

if [[ $RET1 -ne 0 || $RET2 -ne 0 ]]; then
  echo "ℹ️  Les endpoints mock=0 dépendent de /api/ohlcv/ohlcv. Si ça échoue, vérifie OHLCV ou teste en mock=1."
fi

echo "==> Fini ✅"
