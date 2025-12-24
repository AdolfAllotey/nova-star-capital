#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8000"

echo "🔎 Test API Nova Star Capital ($BASE_URL)"

test_endpoint() {
  local url="$1"
  local desc="$2"
  echo -n "➡️  $desc ... "
  if curl -fsS "$url" -o /tmp/resp.json; then
    echo "✅ (HTTP 200)"
    head -c 200 /tmp/resp.json | jq . >/dev/null 2>&1 && jq . /tmp/resp.json | head -n 5 || cat /tmp/resp.json
  else
    echo "❌ (erreur HTTP)"
  fi
}

# ---- Tests ----
test_endpoint "$BASE_URL/health" "Health check"
test_endpoint "$BASE_URL/openapi.json" "OpenAPI schema"
test_endpoint "$BASE_URL/api/ohlcv/ohlcv?symbol=BTCUSDT&tf=1h&limit=5" "OHLCV mock"
test_endpoint "$BASE_URL/api/strategy/_diag" "Strategy diag"
test_endpoint "$BASE_URL/api/strategy/_status" "Strategy status"
test_endpoint "$BASE_URL/api/strategy/allocations" "Strategy allocations"
test_endpoint "$BASE_URL/api/strategy/top?mock=1&tf=1h&limit=5" "Strategy top (mock)"
test_endpoint "$BASE_URL/api/strategy/top?mock=0&tf=1h&limit=5" "Strategy top (real)"

echo "✅ Tests terminés"
