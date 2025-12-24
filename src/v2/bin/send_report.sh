#!/usr/bin/env bash
set -euo pipefail
cd /root/Bot_crypto_ultra
export PYTHONUNBUFFERED=1
export PYTHONPATH=/root/Bot_crypto_ultra
. /root/Bot_crypto_ultra/venv/bin/activate
exec python -m src.v2.scripts.send_reports
