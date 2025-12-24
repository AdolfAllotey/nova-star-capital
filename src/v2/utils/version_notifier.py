# src/v2/utils/version_notifier.py

import os
import json
from datetime import datetime, timezone, timezone
from src.utils.telegram_bot import send_telegram_message

VERSION_FILE = "data/v2/version_history.json"
LAST_SENT_FILE = "data/v2/last_version_sent.json"

os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)

def load_last_sent_version():
    if os.path.exists(LAST_SENT_FILE):
        with open(LAST_SENT_FILE, "r") as f:
            return json.load(f).get("last_version")
    return None

def save_last_sent_version(version_id):
    with open(LAST_SENT_FILE, "w") as f:
        json.dump({"last_version": version_id}, f)

def notify_latest_version():
    if not os.path.exists(VERSION_FILE):
        print("❌ Aucun historique de version trouvé.")
        return

    with open(VERSION_FILE, "r") as f:
        versions = json.load(f)

    if not versions:
        print("❌ Aucune version enregistrée.")
        return

    latest_version = versions[-1]
    last_sent = load_last_sent_version()

    if latest_version["version"] == last_sent:
        print(f"ℹ️ Version {latest_version['version']} déjà notifiée.")
        return

    # Construire le message
    message = f"📦 Nouvelle version du bot : *{latest_version['version']}*\n"
    message += f"🗓️ Date : {latest_version['date']}\n"
    message += f"🧠 Modules : {', '.join(latest_version['modules'])}\n"
    if latest_version["notes"]:
        message += f"📝 Notes : {latest_version['notes']}\n"

    send_telegram_message(message)
    save_last_sent_version(latest_version["version"])
    print(f"✅ Notification envoyée pour la version {latest_version['version']}.")

if __name__ == "__main__":
    notify_latest_version()