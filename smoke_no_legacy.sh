#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8000"

echo "# Health"
curl -fsS "$BASE/health" | jq .

echo "# Ready"
curl -fsS "$BASE/ready"  | jq .

echo "# Metrics (JSON + prom head)"
curl -fsS "$BASE/metrics" | jq .
curl -fsS "$BASE/metrics.prom" | head

echo "# OHLCV mock JSON & CSV"
curl -fsS "$BASE/api/ohlcv/ohlcv?symbol=BTCUSDT&tf=1h&limit=3&mock=1" | jq '.[0]'
curl -fsS "$BASE/api/ohlcv/ohlcv?symbol=BTCUSDT&tf=1h&days=1&format=csv&mock=1" | head

echo "# Strategy mock & real"
curl -fsS "$BASE/api/strategy/top?mock=1&tf=1h&limit=96" | jq .
curl -fsS "$BASE/api/strategy/top?mock=0&tf=1h&limit=96" | jq .

echo "# Legacy must be 404"
code=$(curl -o /dev/null -s -w "%{http_code}" "$BASE/internal/ohlcv/")
test "$code" = "404" && echo "Legacy 404 OK" || { echo "Unexpected: $code"; exit 1; }
