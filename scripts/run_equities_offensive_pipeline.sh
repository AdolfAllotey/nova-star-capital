#!/usr/bin/env bash
set -euo pipefail
cd /opt/nsc/app

export NSC_ENV=PREPROD
export NSC_EQU_ACTION_POLICY=SIMULATED_EXECUTION

echo "== NSC EQUITIES OFFENSIVE PIPELINE =="
python src/v2/equities_offensive/run_equities_pipeline.py

echo "✅ DONE: equities_offensive pipeline OK"
