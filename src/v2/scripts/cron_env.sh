#!/usr/bin/env bash
set -euo pipefail

# ➜ ADAPTE ces chemins à ta machine
export PROJECT_DIR="$HOME/Desktop/Bot_crypto_ultra"
export VENV_DIR="$PROJECT_DIR/venv310"

# PATH riche (utile pour cron)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

# Active le venv
source "$VENV_DIR/bin/activate"

# Va à la racine du projet
cd "$PROJECT_DIR"