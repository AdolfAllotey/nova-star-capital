#!/usr/bin/env bash
set -euo pipefail
BASE="/root/Bot_crypto_ultra"
LOG="$BASE/src/v2/logs/send_reports_$(date -u +%F).log"
DATA="$BASE/src/v2/data/social/telegram_data.json"

ok=0
msg="✅ OK"
if [[ ! -f "$LOG" ]] || ! grep -q "Telegram envoyé = True" "$LOG"; then
  ok=1; msg="❌ Pas de succès Telegram aujourd'hui"
fi
if [[ ! -f "$LOG" ]] || ! grep -q "Email envoyé = True" "$LOG"; then
  ok=1; msg="$msg ; pas de succès Email"
fi
if [[ -f "$DATA" ]]; then
  total=$(python3 - <<'PY'
import json,sys; print(sum(len(c.get("messages",[])) for c in json.load(open(sys.argv[1]))))
PY
"$DATA")
  echo "📊 messages_total=$total"
fi
echo "$msg"
exit $ok
