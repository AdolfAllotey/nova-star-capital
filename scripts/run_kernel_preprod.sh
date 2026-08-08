#!/usr/bin/env bash
set -euo pipefail

export NSC_KERNEL_LOCK="${NSC_KERNEL_LOCK:-/opt/nsc/data/preprod/state/nsc-kernel.lock}"
export NSC_DATA_DIR="${NSC_DATA_DIR:-/opt/nsc/data/preprod}"

echo "[run_kernel_preprod] using lock: $NSC_KERNEL_LOCK"
echo "[run_kernel_preprod] using data dir: $NSC_DATA_DIR"

run_all() {
  echo "[run_kernel_preprod] step 1/6: refresh crypto top movers"
  NSC_DATA_ROOT="$NSC_DATA_DIR" /opt/nsc/.venv/bin/python -m src.v2.jobs.build_top_movers

  echo "[run_kernel_preprod] step 2/6: refresh dynamic crypto token selection"
  /opt/nsc/.venv/bin/python -m src.v2.analysis.token_selector_v2_2

  echo "[run_kernel_preprod] step 3/6: refresh crypto spot prices"
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/market/price_fetcher_crypto.py --data-dir "$NSC_DATA_DIR"

  echo "[run_kernel_preprod] step 4/6: refresh crypto OHLCV"
  /opt/nsc/.venv/bin/python -m src.v2.analysis.price_fetcher

  echo "[run_kernel_preprod] step 5/7: refresh market regime + market conditions"
  /opt/nsc/.venv/bin/python -m src.v2.analysis.market_regime_detector
  /opt/nsc/.venv/bin/python -m src.v2.analysis.market_conditions_engine_pro

  echo "[run_kernel_preprod] step 6/7: run trading kernel"
  /opt/nsc/.venv/bin/python -m src.v2.trading.trading_kernel

  echo "[run_kernel_preprod] step 7/7: refresh master portfolio layer"
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/portfolio_engine_v1.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/portfolio_state_builder.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/master_rebalance_builder.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/master_coherence_audit.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/orchestration_status_builder.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/check_orchestration_consistency.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/global_orchestration_audit.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/supervision_gate_builder.py
  /opt/nsc/.venv/bin/python /opt/nsc/app/src/v2/portfolio/institutional_supervision_summary.py
}

if flock -n "$NSC_KERNEL_LOCK" /bin/bash -lc "$(declare -f run_all); run_all"; then
  exit 0
else
  rc=$?
  echo "ERROR: nsc-kernel run failed with rc=$rc"
  exit "$rc"
fi
