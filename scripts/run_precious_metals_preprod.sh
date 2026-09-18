#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app

export PYTHONPATH=/opt/nsc/app
export NSC_PROJECT_ROOT=/opt/nsc/app
export NSC_ENV=PREPROD
export NSC_DATA_DIR=/opt/nsc/data/preprod
export DATA_ROOT=/opt/nsc/data/preprod
export NSC_DATA_ROOT=/opt/nsc/data/preprod

echo "[run_precious_metals_preprod] start $(date -Is)"

# 1. Collect/provision certified macro inputs through the existing
# FRED runtime, then build the fresh Precious Metals signal and
# Portfolio input.
#
# Important:
# run_metals_pipeline must NOT synthesize metals_state.
# Runtime state becomes authoritative only after the simulated broker.
echo "[run_precious_metals_preprod] step 1/9: FRED runtime + signal + portfolio input"

/opt/nsc/.venv/bin/python - <<'PY_RUNTIME'
from src.v2.precious_metals.macro_provider_runtime import (
    execute_precious_metals_runtime,
)

execute_precious_metals_runtime(
    network_authorized=True,
    provisioning_authorized=True,
    runtime_execution_authorized=True,
    certified_input_authorized=False,
)
PY_RUNTIME

# 2. Refresh the governed Portfolio target from the fresh Metals input.
echo "[run_precious_metals_preprod] step 2/9: governed target refresh"

/opt/nsc/.venv/bin/python \
  /opt/nsc/app/src/v2/portfolio/portfolio_engine_v1.py

# 3. Materialize the new governed target_amount_eur into portfolio_state.
#
# Current Metals exposure may still originate from the previous
# broker-backed metals_state. This pre-refresh exists only so the
# simulated broker receives the fresh governed target.
echo "[run_precious_metals_preprod] step 3/9: pre-execution portfolio state"

/opt/nsc/.venv/bin/python \
  /opt/nsc/app/src/v2/portfolio/portfolio_state_builder.py

# 4. Apply the governed target through the PREPROD simulated broker.
echo "[run_precious_metals_preprod] step 4/9: simulated broker"

/opt/nsc/.venv/bin/python \
  -m src.v2.precious_metals.metals_simulated_broker

# 5. Rebuild Precious Metals runtime state strictly from broker authority.
echo "[run_precious_metals_preprod] step 5/9: broker-backed state"

/opt/nsc/.venv/bin/python \
  -m src.v2.precious_metals.metals_state_updater

# 6. Rebuild Portfolio state from the broker-backed Metals exposure.
echo "[run_precious_metals_preprod] step 6/9: final portfolio state"

/opt/nsc/.venv/bin/python \
  /opt/nsc/app/src/v2/portfolio/portfolio_state_builder.py

# 7. Rebuild master rebalance.
echo "[run_precious_metals_preprod] step 7/9: master rebalance"

/opt/nsc/.venv/bin/python \
  /opt/nsc/app/src/v2/portfolio/master_rebalance_builder.py

# 8. Verify master coherence.
echo "[run_precious_metals_preprod] step 8/9: master coherence"

/opt/nsc/.venv/bin/python \
  /opt/nsc/app/src/v2/portfolio/master_coherence_audit.py

# 9. Refresh downstream capital allocation artifact.
echo "[run_precious_metals_preprod] step 9/9: capital allocator"

/opt/nsc/.venv/bin/python \
  /opt/nsc/app/src/v2/analysis/capital_allocator.py

echo "[run_precious_metals_preprod] done $(date -Is)"
