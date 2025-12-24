import os
import pandas as pd
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv
from datetime import datetime

# 📄 Charger l'environnement
load_dotenv("main.env")

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME")

# 🧠 Crée le client avec session persistante
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

def update_telegram_group_list():
    print("📡 Scraping des groupes Telegram...")

    groups = []
    with client:
        dialogs = client.iter_dialogs()
        for dialog in dialogs:
            entity = dialog.entity
            # On filtre les entités ayant un username ET un titre (groupes / canaux uniquement)
            if hasattr(entity, 'username') and entity.username and hasattr(entity, 'title'):
                groups.append({
                    'name': entity.title,
                    'username': entity.username,
                })

    df = pd.DataFrame(groups)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output_path = "data/social/telegram_groups.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"✅ {len(df)} groupe(s)/canal(aux) détecté(s) avec username")
    print(f"📁 Groupes enregistrés dans {output_path} à {timestamp}")

if __name__ == "__main__":
    update_telegram_group_list()