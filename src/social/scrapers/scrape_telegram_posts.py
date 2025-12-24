# src/social/scrapers/scrape_telegram_posts.py

import os
import pandas as pd
from telethon.sync import TelegramClient
from dotenv import load_dotenv

load_dotenv("env/main.env")

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "botcrypto")

def scrape_telegram_posts(groups_csv_path="data/social/telegram_groups.csv", output_path="data/social/telegram_posts.csv"):
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    client.start()

    if not os.path.exists(groups_csv_path):
        print(f"❌ Fichier introuvable : {groups_csv_path}")
        return pd.DataFrame()

    df = pd.read_csv(groups_csv_path)
    usernames = df["username"].dropna().tolist()
    posts = []

    for username in usernames:
        try:
            entity = client.get_entity(username)
            messages = client.iter_messages(entity, limit=50)
            for message in messages:
                if message.text:
                    posts.append({"group": username, "text": message.text})
        except Exception as e:
            print(f"❌ Erreur {username}: {e}")

    df_posts = pd.DataFrame(posts)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_posts.to_csv(output_path, index=False)
    print(f"✅ {len(df_posts)} messages sauvegardés dans {output_path}")

    return df_posts