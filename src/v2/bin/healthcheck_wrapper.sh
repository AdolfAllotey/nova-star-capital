#!/usr/bin/env bash
set -euo pipefail
BASE="/root/Bot_crypto_ultra"
[ -f "$BASE/src/v2/.env" ] && set -a && . "$BASE/src/v2/.env" && set +a
export PYTHONPATH="$BASE"
exec "$BASE/venv310/bin/python" "$BASE/src/v2/scripts/healthcheck.py"
