import os
import json
import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
from pathlib import Path
from dotenv import load_dotenv

# 📂 Chargement des variables d’environnement
env_path = Path("src/v2/.env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print("⚠️ Fichier .env introuvable à src/v2/.env")

# 🔐 Credentials
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
phone = os.getenv("TELEGRAM_PHONE")  # facultatif si tu veux éviter la saisie manuelle

# 📁 Chemin de sortie
groups_file = Path("src/v2/groups.json")

async def main():
    client = TelegramClient("session_generate", api_id, api_hash)

    if not phone:
        phone_input = input("📱 Entrez votre numéro de téléphone (ex: +33700000000) : ").strip()
    else:
        phone_input = phone

    await client.start(phone=phone_input)

    print("✅ Authentifié en tant que", (await client.get_me()).first_name)

    dialogs = await client.get_dialogs()
    group_list = []

    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)) and getattr(entity, "megagroup", False):
            group_info = {
                "name": entity.title,
                "username": entity.username
            }
            if group_info["username"]:
                group_list.append(group_info)

    groups_file.parent.mkdir(parents=True, exist_ok=True)
    with groups_file.open("w") as f:
        json.dump(group_list, f, indent=4)

    print(f"✅ {len(group_list)} groupes sauvegardés dans {groups_file}")

if __name__ == "__main__":
    asyncio.run(main())