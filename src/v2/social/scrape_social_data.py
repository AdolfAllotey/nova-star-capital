import os
import json
import asyncio
from datetime import datetime, timezone, timezone
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError, UsernameNotOccupiedError
from dotenv import load_dotenv
from src.v2.utils.file_utils import save_json_with_timestamp
from src.v2.utils.telegram_utils import load_telegram_groups

load_dotenv(dotenv_path="src/v2/.env")

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
phone = os.getenv("TELEGRAM_PHONE")

GROUPS_FILE = "src/v2/groups.json"
SAVE_FOLDER = "data/v2/social"
MESSAGES_PER_GROUP = 50

async def scrape_telegram_groups():
    groups = load_telegram_groups(GROUPS_FILE)
    print(f"✅ {len(groups)} groupes chargés depuis {GROUPS_FILE}")

    messages = []

    async with TelegramClient("src/v2/.session", api_id, api_hash) as client:
        await client.start(phone)
        print(f"✅ Authentifié en tant que {await client.get_me().first_name}")

        for group in groups:
            username = group.get("username")
            print(f"🔍 Scraping groupe : {username}")
            try:
                entity = await client.get_entity(username)
                history = await client.get_messages(entity, limit=MESSAGES_PER_GROUP)
                for msg in history:
                    messages.append({
                        "group": username,
                        "date": msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                        "text": msg.message
                    })
            except UsernameNotOccupiedError:
                print(f"❌ Groupe invalide : {username}")
            except FloodWaitError as e:
                print(f"⏳ Attente requise ({e.seconds} sec)...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Erreur avec le groupe {username}: {e}")

    print(f"✅ Scraping terminé. {len(messages)} messages sauvegardés.")
    save_json_with_timestamp(messages, "telegram_messages", folder=SAVE_FOLDER)

if __name__ == "__main__":
    asyncio.run(scrape_telegram_groups())