import os
import csv
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.types import Channel
from datetime import datetime

# 🔐 Chargement des identifiants depuis le fichier .env
load_dotenv()
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_FILE = "src/social/sessions/crypto_session"

def fetch_user_groups():
    """
    Récupère les groupes et canaux Telegram suivis par l'utilisateur.
    Retourne une liste de dictionnaires avec 'name' et 'username'.
    """
    groups = []

    with TelegramClient(SESSION_FILE, API_ID, API_HASH) as client:
        print("🔍 Connexion réussie. Récupération des groupes...")
        dialogs = client.get_dialogs()

        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, Channel):
                name = dialog.name
                username = getattr(entity, "username", "")
                groups.append({"name": name, "username": username})

    return groups

def export_groups_to_csv(groups):
    os.makedirs("data/social", exist_ok=True)
    filename = f"data/social/telegram_groups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["name", "username"])
        writer.writeheader()
        writer.writerows(groups)
    print(f"💾 Groupes exportés dans : {filename}")

if __name__ == "__main__":
    group_list = fetch_user_groups()
    print("\n📋 Groupes trouvés :")
    for g in group_list:
        print(f"• {g['name']} | {g['username']}")
    export_groups_to_csv(group_list)