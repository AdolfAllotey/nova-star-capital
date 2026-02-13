#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${1:-/opt/nsc/app/data/crypto}"

# 1) Fetch prices
/opt/nsc/.venv/bin/python -m src.v2.market.price_fetcher_crypto --data-dir "$DATA_DIR"

# 2) Build execution plan
/opt/nsc/.venv/bin/python -m src.v2.analysis.execution_engine_pro --data-dir "$DATA_DIR"

# 3) Quick view
jq '.orders[] | {symbol, notional_eur, exchange, qty, execution_mode, action}' "$DATA_DIR/trading/execution_plan.json" || true
