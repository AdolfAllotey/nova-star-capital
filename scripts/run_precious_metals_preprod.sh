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
/opt/nsc/.venv/bin/python -m src.v2.precious_metals.run_metals_pipeline
echo "[run_precious_metals_preprod] done $(date -Is)"
