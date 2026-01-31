#!/usr/bin/env bash
set -euo pipefail

LOCK="/opt/nsc/app/data/state/nsc-scrapers.lock"
PY="/opt/nsc/.venv/bin/python"

# si lock pris => on log et on sort 0 (timer OK, pas d'échec)
if /usr/bin/flock -n "$LOCK" "$PY" -m src.v2.monitoring.run_scrapers; then
  exit 0
else
  echo "LOCKED: nsc-scrapers already running"
  exit 0
fi
