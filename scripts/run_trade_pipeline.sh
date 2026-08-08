#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/nsc/app"
LOG_DIR="/opt/nsc/app/src/v2/logs"
PYTHON_BIN="/opt/nsc/app/.venv/bin/python"

TRADE_FILE="/opt/nsc/data/preprod/trading/trade_simulation.json"
SPOT_FILE="/opt/nsc/data/preprod/market/crypto_spot_prices.json"

SIM_SCRIPT="/opt/nsc/app/src/v2/trading/generate_trade_simulation.py"
ENRICH_SCRIPT="/opt/nsc/app/src/v2/trading/enrich_crypto_trades_from_spot.py"

mkdir -p "$LOG_DIR"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%S%z"
}

echo "$(timestamp) | INFO | trade_pipeline | ===== START TRADE PIPELINE ====="

cd "$APP_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "$(timestamp) | ERROR | trade_pipeline | Python introuvable: $PYTHON_BIN"
  exit 1
fi

if [ ! -f "$SIM_SCRIPT" ]; then
  echo "$(timestamp) | ERROR | trade_pipeline | Script simulation introuvable: $SIM_SCRIPT"
  exit 1
fi

if [ ! -f "$ENRICH_SCRIPT" ]; then
  echo "$(timestamp) | ERROR | trade_pipeline | Script enrichissement introuvable: $ENRICH_SCRIPT"
  exit 1
fi

echo "$(timestamp) | INFO | trade_pipeline | Run simulation: $SIM_SCRIPT"
"$PYTHON_BIN" "$SIM_SCRIPT"

if [ ! -f "$TRADE_FILE" ]; then
  echo "$(timestamp) | ERROR | trade_pipeline | trade_simulation.json introuvable après simulation: $TRADE_FILE"
  exit 1
fi

if [ ! -f "$SPOT_FILE" ]; then
  echo "$(timestamp) | ERROR | trade_pipeline | crypto_spot_prices.json introuvable: $SPOT_FILE"
  exit 1
fi

echo "$(timestamp) | INFO | trade_pipeline | Run enrichment: $ENRICH_SCRIPT"
"$PYTHON_BIN" "$ENRICH_SCRIPT"

echo "$(timestamp) | INFO | trade_pipeline | ===== END TRADE PIPELINE ====="
