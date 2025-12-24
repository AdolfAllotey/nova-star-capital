#!/bin/bash

# Se place dans le dossier du script
cd "$(dirname "$0")"

# Lance le script Python
echo "📊 Lancement du backtest..."
python3 src/backtester/backtest_runner.py