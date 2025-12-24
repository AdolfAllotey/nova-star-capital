#!/usr/bin/env bash
set -euo pipefail
cd /root/Bot_crypto_ultra
# Ne PAS sourcer .env ici : on laisse python-dotenv le faire
exec /root/venv310/bin/python - <<'PY'
from dotenv import load_dotenv
load_dotenv(dotenv_path="/root/Bot_crypto_ultra/src/v2/.env")
from src.v2.monitoring.healthcheck import run_healthcheck
run_healthcheck()
PY
