#!/usr/bin/env bash
# Charge l'environnement (.env) s'il existe
: "${TELEGRAM_MESSAGE_LIMIT:=50}"
[ -f "/root/Bot_crypto_ultra/src/v2/.env" ] && set -a && . /root/Bot_crypto_ultra/src/v2/.env && set +a
set -euo pipefail
cd /root/Bot_crypto_ultra
/root/Bot_crypto_ultra/venv310/bin/python -m src.v2.social.telegram_scraper
