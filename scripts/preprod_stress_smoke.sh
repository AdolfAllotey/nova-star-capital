#!/usr/bin/env bash
set -euo pipefail

export NSC_ENV=PREPROD
export PREPROD_SIMULATE_ORDERS=true

runs="${1:-10}"

echo "== PREPROD STRESS SMOKE: runs=$runs =="

before_pos="$(sha256sum data/trading/open_positions.json 2>/dev/null | awk '{print $1}' || true)"

ok_count=0
for i in $(seq 1 "$runs"); do
  echo "-- run $i/$runs"
  ./scripts/preprod_check.sh >/dev/null
  ok="$(jq -r '.ok' data/telemetry/preprod_check.json)"
  if [ "$ok" = "true" ]; then ok_count=$((ok_count+1)); fi
done

after_pos="$(sha256sum data/trading/open_positions.json 2>/dev/null | awk '{print $1}' || true)"

echo "ok_count=$ok_count/$runs"
echo "open_positions_hash_before=$before_pos"
echo "open_positions_hash_after =$after_pos"

if [ "$before_pos" != "$after_pos" ]; then
  echo "❌ open_positions mutated during stress smoke"
  exit 1
fi

if [ "$ok_count" -ne "$runs" ]; then
  echo "❌ some preprod_check runs failed"
  exit 1
fi

echo "✅ stress smoke OK"
