import os
import json
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
session_name = "nova_star_session"

GROUPS_FILE = "groups.json"
OUTPUT_FOLDER = "data/v2/social"
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "telegram_messages.json")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def load_groups():
    with open(GROUPS_FILE, "r") as f:
        return json.load(f)

def extract_tokens(message):
    # À personnaliser : détection de tokens (ex : $ABC, #TOKEN, etc.)
    words = message.split()
    tokens = [w.strip("$#").upper() for w in words if w.startswith(("$", "#")) and len(w) <= 10]
    return list(set(tokens))

def main():
    groups = load_groups()
    results = []

    with TelegramClient(session_name, api_id, api_hash) as client:
        for group in groups:
            try:
                entity = client.get_entity(group["url"])
                messages = client.iter_messages(entity, limit=50)
                for msg in messages:
                    if msg.text:
                        tokens = extract_tokens(msg.text)
                        if tokens:
                            results.append({
                                "group": group["name"],
                                "date": msg.date.isoformat(),
                                "tokens": tokens,
                                "text": msg.text[:300]
                            })
            except Exception as e:
                print(f"❌ Erreur pour {group['name']}: {e}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Scraping terminé. {len(results)} messages pertinents sauvegardés.")

if __name__ == "__main__":
    main()