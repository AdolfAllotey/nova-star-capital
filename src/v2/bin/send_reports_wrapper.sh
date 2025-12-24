#!/usr/bin/env bash
# Charge l'environnement (.env) s'il existe
[ -f "/root/Bot_crypto_ultra/src/v2/.env" ] && set -a && . /root/Bot_crypto_ultra/src/v2/.env && set +a
set -euo pipefail

BASE="/root/Bot_crypto_ultra"
PY="$BASE/venv310/bin/python"
STATE_DIR="$BASE/state"
LOCK_FILE="$STATE_DIR/send_reports.lock"
LAST_FILE="$STATE_DIR/last_send_ts"
KILL_SWITCH="$BASE/.reports.disabled"

mkdir -p "$STATE_DIR"

# Kill switch (fichier OU variable d'env)
if [[ -f "$KILL_SWITCH" ]] || [[ "${NOVA_SKIP_REPORTS:-}" == "1" ]]; then
  echo "⚠ Envoi des rapports désactivé (kill switch)."
  exit 0
fi

# Rate-limit (défaut 300s = 5 min)
COOLDOWN="${NOVA_REPORTS_COOLDOWN:-300}"
now_epoch=$(date +%s)
if [[ -f "$LAST_FILE" ]]; then
  last_epoch=$(cat "$LAST_FILE" 2>/dev/null || echo 0)
  diff=$(( now_epoch - last_epoch ))
  if (( diff < COOLDOWN )); then
    echo "⏱️ Envoi sauté (rate-limit ${COOLDOWN}s, restants ~$((COOLDOWN - diff))s)."
    exit 0
  fi
fi

# Verrou pour éviter les lancements simultanés
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "🔒 Envoi sauté (lock actif)."
  exit 0
fi

# Lancement réel
set +e
"$PY" -m src.v2.scripts.send_reports
code=$?
set -e

# Mémorise le dernier envoi si succès (ou même si échec, au choix)
if [ "$code" -eq 0 ]; then date +%s > "$LAST_FILE"; fi

exit $code
