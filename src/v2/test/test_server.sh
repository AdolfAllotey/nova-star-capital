#!/usr/bin/env bash
set -euo pipefail

TOKEN="2d9624fb5808628625fa9cd4e500a5a86152bc794a66ef23"
BASE="http://127.0.0.1:8000"

echo "=== Test API Nova Star Capital ==="

# 1) Health
echo -n "[health] "
curl -sS "$BASE/health" | jq .

# 2) /api/ohlcv (endpoint public)
echo -n "[api/ohlcv] "
curl -sS "$BASE/api/ohlcv?symbol=BTCUSDT&tf=1h&limit=2" | head -c 200; echo

# DISABLED LEGACY: # 3) /internal/ohlcv sans token (doit renvoyer 401)
echo -n "[internal sans token] "
curl -sS -o /dev/null -w "%{http_code}\n" \
# DISABLED LEGACY:   "$BASE/internal/ohlcv?symbol=BTCUSDT&tf=1h&days=1&format=json"

# DISABLED LEGACY: # 4) /internal/ohlcv avec X-API-Token (CSV attendu)
echo -n "[internal avec X-API-Token] "
# DISABLED LEGACY: curl -sS "$BASE/internal/ohlcv?symbol=ETHUSDT&tf=15m&days=1&format=csv" \
  -H "X-API-Token: $TOKEN" | head -n 5

# DISABLED LEGACY: # 5) /internal/ohlcv avec Authorization: Bearer (JSON attendu)
echo -n "[internal avec Bearer] "
# DISABLED LEGACY: curl -sS "$BASE/internal/ohlcv?symbol=BTCUSDT&tf=1h&days=1&format=json" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0]'
