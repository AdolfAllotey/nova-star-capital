# /root/src/v2/utils/simulate_alert.py
from __future__ import annotations
import argparse
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

def env_get(*names: str) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None

def send_telegram_text(token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": "true",
        "disable_notification": "false",
    }
    enc = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=enc, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as r:
        if r.status != 200:
            raise RuntimeError(f"Telegram HTTP {r.status}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Simuler l'envoi d'une alerte Telegram NSC")
    parser.add_argument("--title", default="Alerte simulée", help="Titre (ligne 1)")
    parser.add_argument("--body", default="Ceci est un test de la chaîne de notification.", help="Corps de l'alerte")
    parser.add_argument("--severity", choices=["info","warn","error","success"], default="info", help="Niveau visuel")
    parser.add_argument("--icon", default="", help="Emoji/icone personnalisé (écrase l'icone par défaut)")
    parser.add_argument("--chat-var", choices=["ALERTS","DAILY","GENERIC"], default="ALERTS",
                        help="Sélectionne la variable d'env pour le chat_id")
    parser.add_argument("--dry-run", action="store_true", help="N'affiche que le rendu, n'envoie pas")
    args = parser.parse_args()

    # Icônes par défaut
    icons = {
        "info": "ℹ️",
        "warn": "⚠️",
        "error": "🚨",
        "success": "✅",
    }
    icon = args.icon or icons.get(args.severity, "ℹ️")

    # Timestamp UTC court
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Rendu style NSC (HTML)
    text = (
        f"{icon} <b>{args.title}</b>\n"
        f"🕒 <i>{ts}</i>\n\n"
        f"{args.body}"
    )

    # ENV
    token = env_get("TELEGRAM_BOT_TOKEN")
    if args.chat_var == "ALERTS":
        chat_id = env_get("TELEGRAM_ALERTS_CHAT_ID", "TELEGRAM_CHAT_ID")
    elif args.chat_var == "DAILY":
        chat_id = env_get("TELEGRAM_DAILY_CHAT_ID", "TELEGRAM_CHAT_ID")
    else:
        chat_id = env_get("TELEGRAM_CHAT_ID", "TELEGRAM_ALERTS_CHAT_ID", "TELEGRAM_DAILY_CHAT_ID")

    if not token or not chat_id:
        print("[simulate_alert][ERROR] Variables d'environnement manquantes.")
        print("  Requis : TELEGRAM_BOT_TOKEN et l'un de TELEGRAM_ALERTS_CHAT_ID / TELEGRAM_DAILY_CHAT_ID / TELEGRAM_CHAT_ID")
        return 2

    print("[simulate_alert] Aperçu du message :")
    print("--------------------------------------------------")
    print(text)
    print("--------------------------------------------------")
    if args.dry_run:
        print("[simulate_alert] DRY-RUN, aucun envoi.")
        return 0

    try:
        send_telegram_text(token, chat_id, text, parse_mode="HTML")
        print("[simulate_alert] Telegram: sent ✅")
        return 0
    except Exception as e:
        print(f"[simulate_alert][ERROR] Telegram send failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
