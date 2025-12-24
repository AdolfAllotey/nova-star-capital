import time
import functools
import traceback
from src.v2.utils.logger import get_logger
from src.v2.utils.telegram_utils import send_telegram_message

logger = get_logger("retry_manager")

def retry_on_failure(
    retries=3,
    delay=5,
    alert_name="Module",
    alert_on_failure=True
):
    """
    Décorateur pour relancer une fonction automatiquement en cas d'échec.
    
    :param retries: nombre de tentatives
    :param delay: délai entre tentatives en secondes
    :param alert_name: nom du module pour les logs et alertes
    :param alert_on_failure: envoie une alerte Telegram après échecs
    """
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    logger.warning(f"{alert_name} – tentative {attempt} échouée : {e}")
                    logger.debug(traceback.format_exc())
                    time.sleep(delay)
            logger.error(f"{alert_name} – échec après {retries} tentatives.")
            if alert_on_failure:
                send_telegram_message(f"❌ {alert_name} a échoué après {retries} tentatives.")
            return None
        return wrapper_retry
    return decorator_retry