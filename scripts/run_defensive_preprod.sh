#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app

export NSC_DATA_DIR="${NSC_DATA_DIR:-/opt/nsc/data/preprod}"
export NSC_PORTFOLIO_WRITER_LOCK="${NSC_PORTFOLIO_WRITER_LOCK:-$NSC_DATA_DIR/state/nsc-portfolio-writer.lock}"

echo "[run_defensive_preprod] start $(date -Is)"
echo "[run_defensive_preprod] Portfolio writer lock: $NSC_PORTFOLIO_WRITER_LOCK"
/opt/nsc/.venv/bin/python -m src.v2.defensive_equities.defensive_pipeline
/opt/nsc/.venv/bin/python -m src.v2.defensive_equities.defensive_simulated_broker
/opt/nsc/.venv/bin/python -m src.v2.defensive_equities.defensive_state_updater

# Refresh modern portfolio artifacts after defensive signal update.
# Serialize the complete shared Portfolio write sequence.
exec 9>"$NSC_PORTFOLIO_WRITER_LOCK"
if ! flock -x -w 30 9; then
      echo "ERROR: timed out after 30s waiting for shared Portfolio writer lock" >&2
      exit 75
    fi
echo "[run_defensive_preprod] acquired shared Portfolio writer lock"

/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/portfolio_engine_v1.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/portfolio_state_builder.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/master_rebalance_builder.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/master_coherence_audit.py
/opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/analysis/capital_allocator.py

echo "[run_defensive_preprod] done $(date -Is)"
