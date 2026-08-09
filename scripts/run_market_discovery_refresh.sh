#!/usr/bin/env bash
set -uo pipefail

APP_DIR="/opt/nsc/app"
DATA_DIR="${NSC_DATA_DIR:-/opt/nsc/data/preprod}"
LOCK_FILE="/run/lock/nsc-market-discovery-refresh.lock"

if [ -x /opt/nsc/.venv/bin/python3 ]; then
  PYTHON="/opt/nsc/.venv/bin/python3"
elif [ -x /opt/nsc-venv/bin/python ]; then
  PYTHON="/opt/nsc-venv/bin/python"
else
  echo "FATAL: no NSC Python interpreter found" >&2
  exit 1
fi

mkdir -p "$(dirname "$LOCK_FILE")"
mkdir -p "$DATA_DIR/market" "$DATA_DIR/discovery"

exec 9>"$LOCK_FILE"

if ! flock -n 9; then
  echo "STATUS=SKIPPED"
  echo "REASON=ANOTHER_PROVIDER_REFRESH_IS_RUNNING"
  exit 0
fi

cd "$APP_DIR" || exit 1

export PYTHONPATH="$APP_DIR"
export NSC_DATA_DIR="$DATA_DIR"
export DATA_DIR="$DATA_DIR"
export NSC_DATA_ROOT="$DATA_DIR"
export DATA_ROOT="$DATA_DIR"

RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FAILURES=0

echo "RUN_STARTED_AT=$RUN_STARTED_AT"
echo "PYTHON=$PYTHON"
echo "DATA_DIR=$DATA_DIR"

invalidate_provider() {
  local provider="$1"
  local output="$2"
  local reason="$3"

  "$PYTHON" - "$provider" "$output" "$reason" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys

provider, output, reason = sys.argv[1:4]
path = Path(output)
path.parent.mkdir(parents=True, exist_ok=True)

document = {
    "status": "error",
    "source": provider,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "items": [],
    "message": reason,
}

temporary = path.with_name(f".{path.name}.tmp")
temporary.write_text(
    json.dumps(document, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
os.replace(temporary, path)
PY
}

run_required() {
  local name="$1"
  local module="$2"
  local output="$3"

  echo
  echo "STEP=$name"

  if "$PYTHON" -m "$module"; then
    echo "STEP_RESULT=${name}:PASS"
    return 0
  fi

  rc=$?
  echo "STEP_RESULT=${name}:FAIL:${rc}" >&2
  invalidate_provider \
    "$name" \
    "$output" \
    "Provider refresh failed with exit code ${rc}"
  FAILURES=$((FAILURES + 1))
  return 0
}

run_nonblocking() {
  local name="$1"
  local module="$2"

  echo
  echo "STEP=$name"

  if "$PYTHON" -m "$module"; then
    echo "STEP_RESULT=${name}:PASS_OR_DECLARED_UNAVAILABLE"
    return 0
  fi

  rc=$?
  echo "STEP_RESULT=${name}:FAIL_NONBLOCKING:${rc}" >&2
  FAILURES=$((FAILURES + 1))
  return 0
}

echo
echo "===== BINANCE TOP MOVERS ====="

if "$PYTHON" -m src.v2.jobs.build_top_movers; then
  echo "STEP_RESULT=BINANCE_TOP_MOVERS:PASS"
else
  rc=$?
  echo "STEP_RESULT=BINANCE_TOP_MOVERS:FAIL:${rc}" >&2
  invalidate_provider \
    "binance" \
    "$DATA_DIR/market/top_movers.json" \
    "Binance Top Movers refresh failed with exit code ${rc}"
  FAILURES=$((FAILURES + 1))
fi

echo
echo "===== COINGECKO ====="

run_required \
  "coingecko" \
  "src.v2.discovery.coingecko_discovery" \
  "$DATA_DIR/market/coingecko_top_movers.json"

echo
echo "===== COINMARKETCAP ====="

# Le module produit lui-même status=missing_api_key et items=[]
# lorsqu'aucune clé n'est disponible. Ce cas n'arrête pas le pipeline.
run_nonblocking \
  "coinmarketcap" \
  "src.v2.discovery.coinmarketcap_discovery"

echo
echo "===== BITPANDA ====="

run_required \
  "bitpanda" \
  "src.v2.discovery.bitpanda_discovery" \
  "$DATA_DIR/market/bitpanda_top_movers.json"

echo
echo "===== COMBINED TOP MOVERS ====="

if "$PYTHON" -m src.v2.jobs.build_top_movers_combined; then
  echo "STEP_RESULT=COMBINED_TOP_MOVERS:PASS"
else
  rc=$?
  echo "STEP_RESULT=COMBINED_TOP_MOVERS:FAIL:${rc}" >&2
  FAILURES=$((FAILURES + 1))
fi

echo
echo "===== MARKET DISCOVERY ENGINE ====="

if "$PYTHON" -m src.v2.discovery.market_discovery_engine; then
  echo "STEP_RESULT=MARKET_DISCOVERY_ENGINE:PASS"
else
  rc=$?
  echo "STEP_RESULT=MARKET_DISCOVERY_ENGINE:FAIL:${rc}" >&2
  FAILURES=$((FAILURES + 1))
fi


echo
echo "===== DISCOVERY PERSISTENCE ====="

run_nonblocking \
  "discovery_persistence" \
  "src.v2.discovery.discovery_persistence"

echo
echo "===== PERSISTENCE OPPORTUNITIES ====="

run_nonblocking \
  "persistence_opportunities" \
  "src.v2.discovery.persistence_opportunities"

echo
echo "===== META RANKING ====="

run_nonblocking \
  "meta_ranking" \
  "src.v2.discovery.meta_ranking_engine"

echo
echo "===== META VALIDATION ====="

run_nonblocking \
  "meta_validation" \
  "src.v2.discovery.meta_validation_engine"

echo
echo "===== META VALIDATION HISTORY ====="

run_nonblocking \
  "meta_validation_history" \
  "src.v2.discovery.meta_validation_history"

echo
echo "===== TRADABLE OPPORTUNITIES ====="

run_nonblocking \
  "tradable_opportunities" \
  "src.v2.discovery.tradable_opportunities"

echo
echo "===== META HEALTH MONITOR ====="

run_nonblocking \
  "meta_health_monitor" \
  "src.v2.discovery.meta_health_monitor"

RUN_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo
echo "RUN_FINISHED_AT=$RUN_FINISHED_AT"
echo "FAILURES=$FAILURES"

if [ "$FAILURES" -gt 0 ]; then
  echo "FINAL_STATUS=PASS_WITH_PROVIDER_FAILURES"
  exit 0
fi

echo "FINAL_STATUS=PASS"
exit 0
