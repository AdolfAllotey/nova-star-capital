#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app
/opt/nsc/.venv/bin/python src/v2/analysis/long_term_profit_collector.py
/opt/nsc/.venv/bin/python -m src.v2.analysis.long_term_auto_allocator
/opt/nsc/.venv/bin/python -m src.v2.analysis.long_term_funding_processor
/opt/nsc/.venv/bin/python src/v2/analysis/long_term_valuation.py
/opt/nsc/.venv/bin/python src/v2/analysis/long_term_nav_history.py
/opt/nsc/.venv/bin/python src/v2/analysis/long_term_attribution_engine.py
