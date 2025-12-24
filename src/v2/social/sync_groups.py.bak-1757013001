import asyncio
import json
import os
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELEGRAM_SESSION", "anon")

GROUPS_JSON_PATH = "src/v2/groups.json"

async def fetch_groups():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()

    result = await client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=200,
        hash=0
    ))

    groups = []
    for chat in result.chats:
        if getattr(chat, 'megagroup', False) or getattr(chat, 'broadcast', False):
            groups.append({
                "id": chat.id,
                "name": chat.title,
                "enabled": True
            })

    await client.disconnect()
    return groups

def load_existing_groups():
    if os.path.exists(GROUPS_JSON_PATH):
        with open(GROUPS_JSON_PATH, "r") as f:
            return json.load(f)
    return []

def save_groups(groups):
    with open(GROUPS_JSON_PATH, "w") as f:
        json.dump(groups, f, indent=2)

def merge_groups(existing, new):
    existing_ids = {g['id'] for g in existing}
    merged = existing[:]
    for g in new:
        if g['id'] not in existing_ids:
            merged.append(g)
    return merged

async def main():
    print("🔍 Récupération des groupes Telegram...")
    new_groups = await fetch_groups()
    existing_groups = load_existing_groups()
    all_groups = merge_groups(existing_groups, new_groups)
    save_groups(all_groups)
    print(f"✅ {len(new_groups)} groupes détectés, {len(all_groups)} au total dans groups.json")

if __name__ == "__main__":
    asyncio.run(main())
