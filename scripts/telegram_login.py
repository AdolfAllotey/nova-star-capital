import os
from telethon import TelegramClient

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]

data_dir = (
    os.environ.get("NSC_DATA_DIR")
    or os.environ.get("DATA_ROOT")
    or "data"
)

session = os.path.join(data_dir, "state", "telegram_user")

print("📂 Session path :", session + ".session")

client = TelegramClient(session, api_id, api_hash)

# INTERACTIF : téléphone + code SMS (+ 2FA si activée)
client.start()

print("✅ USER SESSION TELEGRAM OK")
client.disconnect()
