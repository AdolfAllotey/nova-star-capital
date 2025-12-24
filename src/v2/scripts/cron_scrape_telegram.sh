#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/cron_env.sh"

LOG_DIR="$PROJECT_DIR/src/v2/logs"
mkdir -p "$LOG_DIR"

echo "[$(date '+%F %T')] ▶️ Scraping Telegram" | tee -a "$LOG_DIR/cron_telegram_scrape.log"

# Lancement direct de l'async
if python3 - <<'PY' >> "$LOG_DIR/cron_telegram_scrape.log" 2>&1:
import asyncio
from src.v2.monitoring.telegram_scraper import scrape_telegram
asyncio.run(scrape_telegram())
PY
then
  echo "[$(date '+%F %T')] ✅ Scraping Telegram OK" | tee -a "$LOG_DIR/cron_telegram_scrape.log"
else
  EC=$?
  MSG="❌ Scraping Telegram échoué (code=$EC) — voir logs: src/v2/logs/cron_telegram_scrape.log"
  echo "[$(date '+%F %T')] $MSG" | tee -a "$LOG_DIR/cron_telegram_scrape.log"
  python3 - <<'PY'
from src.v2.utils.telegram_utils import send_telegram_message
send_telegram_message("🚨 *Nova Star Capital*\n❌ _Scraping Telegram échoué_\nConsulte les logs: `src/v2/logs/cron_telegram_scrape.log`")
PY
  exit $EC
fi