#!/bin/bash
# Script pour exécuter le pipeline complet Nova Star Capital

APP_DIR="/root/Bot_crypto_ultra"
PYTHON="$APP_DIR/venv310/bin/python"

cd "$APP_DIR" || exit 1

echo "🚀 Lancement du pipeline complet..."
$PYTHON src/v2/main.py