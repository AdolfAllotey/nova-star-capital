#!/usr/bin/env bash
set -euo pipefail

LOCK="/opt/nsc/app/data/state/nsc-scrapers.lock"
PY="/opt/nsc/.venv/bin/python"

logger -t nsc-scrapers "[run_scrapers.sh] NSC_ENV=${NSC_ENV:-} NSC_DATA_DIR=${NSC_DATA_DIR:-} DATA_DIR=${DATA_DIR:-} TWITTER_ENABLED=${TWITTER_ENABLED:-}"
# si lock pris => on log et on sort 0 (timer OK, pas d'échec)
if /usr/bin/flock -n "$LOCK" "$PY" -m src.v2.monitoring.run_scrapers; then
  exit 0
else
  echo "LOCKED: nsc-scrapers already running"
  exit 0
fi
