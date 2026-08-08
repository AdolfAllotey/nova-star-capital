#!/usr/bin/env bash
set -euo pipefail

cd /opt/nsc/app
/opt/nsc/.venv/bin/python -m src.v2.analysis.long_term_funding_processor
/opt/nsc/.venv/bin/python src/v2/analysis/long_term_valuation.py
/opt/nsc/.venv/bin/python src/v2/analysis/long_term_nav_history.py
