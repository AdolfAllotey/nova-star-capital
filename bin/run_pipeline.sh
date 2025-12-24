#!/usr/bin/env bash
set -euo pipefail
cd /root/Bot_crypto_ultra
if [[ ! -x "venv/bin/python3" ]]; then
  echo "❌ venv/bin/python3 introuvable. Crée le venv dans /root/Bot_crypto_ultra/venv"
  exit 1
fi
source venv/bin/activate
exec python3 -m src.v2.main
