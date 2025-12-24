#!/bin/bash
# Script pour lancer uniquement le scraping Telegram

APP_DIR="/root/Bot_crypto_ultra"
PYTHON="$APP_DIR/venv310/bin/python"

cd "$APP_DIR" || exit 1

echo "🔎 Scraping Telegram..."
$PYTHON -m src.v2.monitoring.telegram_scraper