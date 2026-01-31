import os
import logging
import requests

logger = logging.getLogger(__name__)

def send_telegram_message(message: str, parse_mode: str | None = None, *, token: str | None = None, chat_id: str | None = None, timeout: int = 10) -> bool:
    """
    Envoie un message Telegram.
    - Charge TELEGRAM_TOKEN / TELEGRAM_CHAT_ID à l'exécution (pas à l'import)
    - Retourne True/False
    """
    token = (token or os.getenv("TELEGRAM_TOKEN") or "").strip()
    chat_id = str(chat_id or os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not token:
        logger.warning("TELEGRAM_TOKEN non défini (message non envoyé).")
        return False

    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID non défini (message non envoyé).")
        return False

    # robust utf-8
    try:
        text = str(message).encode("utf-8", "replace").decode("utf-8")
    except Exception:
        logger.exception("Erreur encodage du message")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        r = requests.post(url, data=payload, timeout=timeout)
        if r.status_code != 200:
            logger.error("Erreur envoi Telegram: %s - %s", r.status_code, r.text)
            return False
        return True
    except Exception:
        logger.exception("Exception envoi Telegram")
        return False
