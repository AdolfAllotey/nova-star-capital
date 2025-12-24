import os
import pandas as pd
from telethon.sync import TelegramClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "anon")

DATA_PATH = "data/social"
os.makedirs(DATA_PATH, exist_ok=True)
CSV_PATH = os.path.join(DATA_PATH, "telegram_groups.csv")


def update_telegram_group_list():
    with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        dialogs = client.get_dialogs()
        groups = []

        for dialog in dialogs:
            entity = dialog.entity
            if hasattr(entity, "username") and entity.username:
                groups.append({
                    "name": entity.title if hasattr(entity, "title") else entity.first_name,
                    "username": entity.username
                })

        df = pd.DataFrame(groups)
        df.drop_duplicates(subset="username", inplace=True)
        df.to_csv(CSV_PATH, index=False)

        print(f"✅ {len(df)} groupe(s)/canal(aux) détecté(s) avec username")
        print(f"📁 Groupes enregistrés dans {CSV_PATH} à {datetime.now()}")