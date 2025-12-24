
import logging
import os
from datetime import datetime, timezone, timezone

def setup_logger(name="bot_logger", log_dir="logs", level=logging.INFO):
    os.makedirs(log_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(log_dir, f"{date_str}_bot.log")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger

# Exemple d'utilisation :
# logger = setup_logger()
# logger.info("Bot démarré.")
# logger.error("Erreur critique.")
