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
echo "[run_precious_metals_preprod] done $(date -Is)"
