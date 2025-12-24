#!/bin/bash
# Script pour envoyer uniquement le rapport (sans relancer tout le pipeline)

APP_DIR="/root/Bot_crypto_ultra"
PYTHON="$APP_DIR/venv310/bin/python"

cd "$APP_DIR" || exit 1

echo "✉️ Envoi du rapport..."
$PYTHON -m src.v2.scripts.send_reports