import os
from dotenv import load_dotenv
from telethon import TelegramClient

# Charger les variables d'environnement
load_dotenv("telegram.env")
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")

# Créer le client Telegram (session nommée "test")
client = TelegramClient("test", api_id, api_hash)

async def main():
    me = await client.get_me()
    print(f"✅ Connecté en tant que : {me.first_name} (@{me.username})")

with client:
    client.loop.run_until_complete(main())
