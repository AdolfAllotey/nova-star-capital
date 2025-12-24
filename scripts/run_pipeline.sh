#!/usr/bin/env bash
set -euo pipefail
cd /root/Bot_crypto_ultra
LOG_DIR="src/v2/logs"
mkdir -p "$LOG_DIR"

# Boucle infinie : lance le pipeline, puis dort un peu
while true; do
  echo "$(date '+%F %T') - [pipeline] run" | tee -a "$LOG_DIR/pipeline_loop.log"
  /root/Bot_crypto_ultra/venv310/bin/python -m src.v2.main || true
  sleep 120
done
