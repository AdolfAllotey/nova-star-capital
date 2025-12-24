import traceback
from functools import wraps
from src.v2.utils.logger import get_logger
from src.v2.utils.telegram_utils import send_telegram_report

logger = get_logger("error_notifier")


def alert_on_failure(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = f"❌ Erreur critique dans le pipeline principal\n\n{traceback.format_exc()}"
            logger.error(error_message)
            try:
                send_telegram_report(error_message)
            except Exception as send_err:
                logger.error(f"Erreur lors de l'envoi de l'alerte Telegram : {send_err}")
            raise e
    return wrapper