import os
import time
import subprocess
from datetime import datetime, timezone, timezone, timedelta
from src.v2.utils.logger import get_logger
from src.v2.utils.telegram_utils import send_telegram_message

# Modules à surveiller (nom + chemin)
MODULES_TO_WATCH = {
    "generate_trade_simulation": "src/trading/generate_trade_simulation.py",
    "generate_daily_report": "src/reporting/generate_daily_report.py",
    "telegram_scraper": "src/social/telegram_scraper.py",
    # Ajoute ici les modules essentiels de ton bot
}

# Seuil max d'inactivité (en minutes)
INACTIVITY_THRESHOLD_MINUTES = 15

# Logger dédié
logger = get_logger("watchdog")

def is_module_active(log_file_path: str) -> bool:
    """Vérifie si un module a écrit dans son log récemment"""
    try:
        last_mod_time = datetime.fromtimestamp(os.path.getmtime(log_file_path))
        return datetime.now() - last_mod_time < timedelta(minutes=INACTIVITY_THRESHOLD_MINUTES)
    except FileNotFoundError:
        logger.warning(f"Fichier log manquant : {log_file_path}")
        return False

def restart_module(script_path: str, module_name: str):
    """Tente de relancer un module en erreur"""
    logger.error(f"{module_name} inactif. Redémarrage en cours...")
    send_telegram_message(f"🛑 {module_name} inactif. Tentative de redémarrage...")
    subprocess.Popen(["python3", script_path])
    logger.info(f"{module_name} redémarré.")

def main():
    logger.info("Watchdog lancé. Surveillance des modules...")
    while True:
        for module_name, script_path in MODULES_TO_WATCH.items():
            log_path = f"src/v2/logs/{module_name}.log"
            if not is_module_active(log_path):
                restart_module(script_path, module_name)
        time.sleep(300)  # vérifie toutes les 5 minutes

if __name__ == "__main__":
    main()