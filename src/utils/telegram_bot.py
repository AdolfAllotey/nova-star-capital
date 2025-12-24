import os
import requests

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5308497197")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def send_telegram_message(message: str, parse_mode: str = None):
    """
    Envoie un message Telegram avec prise en charge facultative de Markdown ou HTML.
    Gère les emojis et caractères spéciaux en UTF-8.
    """
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN non défini.")
        return

    try:
        message = message.encode("utf-8", "replace").decode("utf-8")
    except Exception as e:
        print(f"❌ Erreur encodage du message : {e}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Erreur envoi Telegram : {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception envoi Telegram : {e}")