#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/cron_env.sh"

LOG_DIR="$PROJECT_DIR/src/v2/logs"
mkdir -p "$LOG_DIR"

echo "[$(date '+%F %T')] ▶️ Lancement pipeline" | tee -a "$LOG_DIR/cron_pipeline.log"

# Exécute le pipeline
if python3 -m src.v2.main >> "$LOG_DIR/cron_pipeline.log" 2>&1; then
  echo "[$(date '+%F %T')] ✅ Pipeline OK" | tee -a "$LOG_DIR/cron_pipeline.log"
else
  EC=$?
  MSG="❌ Pipeline échoué (code=$EC) — voir logs: src/v2/logs/cron_pipeline.log"
  echo "[$(date '+%F %T')] $MSG" | tee -a "$LOG_DIR/cron_pipeline.log"
  # Alerte Telegram
  python3 - <<'PY'
from src.v2.utils.telegram_utils import send_telegram_message
send_telegram_message("🚨 *Nova Star Capital*\n❌ _Pipeline échoué_\nConsulte les logs: `src/v2/logs/cron_pipeline.log`")
PY
  exit $EC
fi