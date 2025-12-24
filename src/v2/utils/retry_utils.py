
import time
import functools
import logging
import requests

# Remplace ceci par ton token et chat_id Telegram
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi Telegram : {e}")

def retry_on_failure(max_retries=3, delay=5, backoff=2, module_name=""):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    error_msg = (f"[Retry] Erreur dans le module '{module_name}' "
                                 f"(tentative {retries}/{max_retries}): {e}")
                    logging.warning(error_msg)
                    if retries == max_retries:
                        critical_msg = (f"⚠️ Bot Crypto Ultra — ERREUR CRITIQUE\n"
                                        f"Module : {module_name}\n"
                                        f"Détail : {e}\n"
                                        f"Action : Échec après {max_retries} tentatives.")
                        send_telegram_alert(critical_msg)
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
