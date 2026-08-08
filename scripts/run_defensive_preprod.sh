#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app

echo "[run_defensive_preprod] start $(date -Is)"
/opt/nsc/.venv/bin/python -m src.v2.defensive_equities.defensive_pipeline
/opt/nsc/.venv/bin/python -m src.v2.defensive_equities.defensive_state_updater

# Refresh modern portfolio artifacts after defensive signal update
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/portfolio_engine_v1.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/portfolio_state_builder.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/master_rebalance_builder.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/master_coherence_audit.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/analysis/capital_allocator.py

echo "[run_defensive_preprod] done $(date -Is)"
