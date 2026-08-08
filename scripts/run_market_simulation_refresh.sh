#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app

echo "[market_sim_refresh] start $(date -Is)"

python /opt/nsc/app/scripts/simulate_market_prices.py
python /opt/nsc/app/src/v2/equities_offensive/market/sync_prices.py
python /opt/nsc/app/src/v2/portfolio/offensive_equity_curve_updater.py
python /opt/nsc/app/src/v2/trading/enrich_crypto_trades_from_spot.py

systemctl restart nsc-api.service

echo "[market_sim_refresh] done $(date -Is)"
