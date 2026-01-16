#!/usr/bin/env bash
set -euo pipefail

export NSC_ENV=PREPROD
export PREPROD_SIMULATE_ORDERS=true

mkdir -p data/telemetry/preprod_runs

ts="$(date -u +%Y%m%d_%H%M%S)"
out_json="data/telemetry/preprod_runs/preprod_daily_${ts}.json"
out_md="data/telemetry/preprod_runs/preprod_daily_${ts}.md"

# 1) Core checks
./scripts/preprod_check.sh >/dev/null
cp -a data/telemetry/preprod_check.json "$out_json"
cp -a data/telemetry/preprod_check.md   "$out_md"

# 2) Knowledge snapshot (best-effort)
python -m src.v2.intelligence.knowledge_daily_generator >/dev/null 2>&1 || true

# 3) Optional stress smoke (set PREPROD_STRESS_RUNS=10)
runs="${PREPROD_STRESS_RUNS:-0}"
if [ "${runs}" != "0" ]; then
  ./scripts/preprod_stress_smoke.sh "${runs}"
fi

# 4) Aggregate KPIs
python scripts/preprod_aggregate_kpis.py >/dev/null 2>&1 || true

echo "✅ preprod daily run saved:"
echo " - $out_json"
echo " - $out_md"
echo " - data/telemetry/preprod_runs/preprod_kpis.json"

# notify on failure (best-effort)
python scripts/preprod_notify.py >/dev/null 2>&1 || true
