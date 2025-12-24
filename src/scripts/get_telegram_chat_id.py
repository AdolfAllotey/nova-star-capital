import os
import requests
from dotenv import load_dotenv

load_dotenv("env/main.env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    print("👉 Envoie d'abord un message à ton bot sur Telegram, puis exécute ce script.")
    input("Appuie sur Entrée une fois que c’est fait...")

    response = requests.get(url)
    data = response.json()

    if data["ok"] and data["result"]:
        chat_id = data["result"][-1]["message"]["chat"]["id"]
        print(f"✅ Ton TELEGRAM_CHAT_ID est : {chat_id}")
    else:
        print("❌ Impossible de récupérer le chat_id. Vérifie que tu as bien envoyé un message au bot.")

if __name__ == "__main__":
    get_chat_id()