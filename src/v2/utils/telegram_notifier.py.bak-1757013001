
import requests
import json
from src.v2.utils.config_loader import load_config

def send_telegram_message(message: str):
    try:
        config = load_config()
        bot_token = config["telegram"]["api_key"]
        chat_id = config["telegram"]["chat_id"]

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            raise Exception(f"Erreur Telegram : {response.text}")
    except Exception as e:
        print(f"[TelegramNotifier] Échec de l'envoi Telegram : {e}")
