# src/v2/tools/generate_valid_groups.py

import os
import json
from telethon.sync import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

OUTPUT_FILE = "src/v2/groups.json"

def generate_valid_groups():
    with TelegramClient("session_scraper", API_ID, API_HASH) as client:
        client.connect()

        if not client.is_user_authorized():
            client.send_code_request(PHONE)
            client.sign_in(PHONE, input("Enter the code you received: "))

        dialogs = client.get_dialogs()
        groups = []

        for dialog in dialogs:
            entity = dialog.entity
            if hasattr(entity, "megagroup") and entity.megagroup:
                group_name = entity.username if entity.username else entity.title
                if group_name:
                    groups.append({"name": group_name})

        with open(OUTPUT_FILE, "w") as f:
            json.dump(groups, f, indent=4)

        print(f"✅ {len(groups)} groupes valides enregistrés dans {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_valid_groups()