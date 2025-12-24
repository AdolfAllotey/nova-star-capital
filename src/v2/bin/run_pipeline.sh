#!/usr/bin/env bash
# Charge l'environnement (.env) s'il existe
[ -f "/root/Bot_crypto_ultra/.env" ] && set -a && . /root/Bot_crypto_ultra/.env && set +a
set -euo pipefail
cd /root/Bot_crypto_ultra
export PYTHONUNBUFFERED=1
export PYTHONPATH=/root/Bot_crypto_ultra
. /root/Bot_crypto_ultra/venv/bin/activate
exec python -m src.v2.main
