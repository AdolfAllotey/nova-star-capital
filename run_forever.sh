#!/bin/bash

echo "🔄 Lancement du bot en continu..."

while true
do
  echo "⏱️ $(date) - Lancement de la simulation..."
  PYTHONPATH=src /root/Bot_crypto_ultra/venv310/bin/python3 src/trading/simulator_live.py
  echo "💤 Pause 30 minutes..."
  sleep 1800
done
