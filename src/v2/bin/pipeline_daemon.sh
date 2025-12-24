#!/usr/bin/env bash
# Charge l'environnement (.env) s'il existe
[ -f "/root/Bot_crypto_ultra/src/v2/.env" ] && set -a && . /root/Bot_crypto_ultra/src/v2/.env && set +a
set -euo pipefail

APP_DIR="/root/Bot_crypto_ultra"

# --- auto-détection du binaire python dans le venv ---
if [[ -x "$APP_DIR/venv310/bin/python3" ]]; then
  PY="$APP_DIR/venv310/bin/python3"
elif [[ -x "$APP_DIR/venv/bin/python3" ]]; then
  PY="$APP_DIR/venv/bin/python3"
else
  PY="$(command -v python3 || true)"
fi

if [[ -z "${PY:-}" || ! -x "$PY" ]]; then
  echo "ERREUR: python3 introuvable (venv non détecté)." >&2
  exit 1
fi

cd "$APP_DIR"

# Empêcher l'envoi de rapports depuis le pipeline en continu

# Intervalle entre deux ticks (en secondes)
INTERVAL_SECONDS=300

while true; do
  echo "[$(date -u +'%F %T')] tick: démarrage pipeline…" >&2
  # On exécute le pipeline complet (sans envoyer de rapport, cf. env ci-dessus)
  "$PY" -m src.v2.main || echo "[$(date -u +'%F %T')] pipeline exit code=$?" >&2
  sleep "$INTERVAL_SECONDS"
done
