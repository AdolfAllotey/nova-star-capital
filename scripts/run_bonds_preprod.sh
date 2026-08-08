#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app
export PYTHONPATH=/opt/nsc/app
export NSC_PROJECT_ROOT=/opt/nsc/app
export NSC_ENV=PREPROD
export NSC_DATA_DIR=/opt/nsc/data/preprod
export DATA_ROOT=/opt/nsc/data/preprod
export NSC_DATA_ROOT=/opt/nsc/data/preprod

echo "[run_bonds_preprod] start $(date -Is)"
/opt/nsc/.venv/bin/python -m src.v2.bonds.run_bonds_pipeline
echo "[run_bonds_preprod] done $(date -Is)"
