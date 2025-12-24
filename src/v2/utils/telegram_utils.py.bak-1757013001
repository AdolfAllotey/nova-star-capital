import os, urllib.request, urllib.parse, json
from src.v2.utils.logger import get_logger
logger = get_logger("telegram_utils")

def send_telegram_message(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID non définis — alerte ignorée")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode()
            j = json.loads(err)
            logger.warning(f"Telegram HTTPError {e.code}: {j.get('description')}")
        except Exception:
            logger.warning(f"Telegram HTTPError {e.code}")
        return False
    except Exception as e:
        logger.warning(f"Echec envoi Telegram: {e}")
        return False
