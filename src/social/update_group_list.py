import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.types import Channel, Chat
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

load_dotenv()

# 🔐 Identifiants API depuis le fichier .env
api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
session_file = "src/social/sessions/crypto_session"

GROUP_LIST_PATH = "group_list.txt"
NEW_GROUPS_PATH = "new_groups.txt"

def load_existing_groups():
    if not os.path.exists(GROUP_LIST_PATH):
        return set()
    with open(GROUP_LIST_PATH, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_group_list(groups):
    with open(GROUP_LIST_PATH, "w") as f:
        for g in sorted(groups):
            f.write(g + "\n")

def save_new_groups(new_groups):
    with open(NEW_GROUPS_PATH, "w") as f:
        for g in sorted(new_groups):
            f.write(g + "\n")

def update_group_list():
    with TelegramClient(session_file, api_id, api_hash) as client:
        existing = load_existing_groups()
        current = set()

        result = client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=1000,
            hash=0
        ))

        for dialog in result.chats:
            if isinstance(dialog, (Channel, Chat)) and getattr(dialog, "username", None):
                current.add(dialog.username)

        new_groups = current - existing

        save_group_list(current)

        if new_groups:
            save_new_groups(new_groups)
            print(f"✅ {len(new_groups)} nouveau(x) groupe(s) détecté(s) et enregistré(s) dans {NEW_GROUPS_PATH}")
            for g in new_groups:
                print("➕", g)
        else:
            print("✅ Aucun nouveau groupe détecté.")

if __name__ == "__main__":
    update_group_list()