import json
import os
from datetime import datetime, timezone, timezone
from src.v2.utils.telegram_utils import send_telegram_message
from src.v2.utils.logger import get_logger

logger = get_logger("gain_protector")

PERFORMANCE_FILE = "data/v2/performance/global_gains.json"
THRESHOLD_EUR = 500  # Modifiable dans la V2 via config
ALERT_ENABLED = True

def load_global_gain():
    if not os.path.exists(PERFORMANCE_FILE):
        logger.warning(f"⚠️ Fichier de performance non trouvé : {PERFORMANCE_FILE}")
        return 0

    try:
        with open(PERFORMANCE_FILE, "r") as f:
            data = json.load(f)
        return data.get("cumulative_gain_eur", 0)
    except Exception as e:
        logger.error(f"❌ Erreur lecture performance : {e}")
        return 0

def secure_gains():
    logger.info("🛡️ Démarrage du module de sécurisation des gains...")

    gain = load_global_gain()
    logger.info(f"💹 Gain cumulé actuel : {gain} €")

    if gain >= THRESHOLD_EUR:
        message = (
            f"🛡️ *Sécurisation de Gains Activée*\n"
            f"Gain cumulé : *{gain} €* (seuil : {THRESHOLD_EUR} €)\n"
            f"🎯 Action recommandée : transfert vers sous-compte sécurité."
        )
        logger.warning("🎯 Gain dépasse le seuil — alerte activée.")
        if ALERT_ENABLED:
            try:
                send_telegram_message(message, parse_mode="Markdown")
                logger.info("✅ Alerte Telegram envoyée.")
            except Exception as e:
                logger.error(f"❌ Erreur envoi Telegram : {e}")
    else:
        logger.info("📉 Gain en dessous du seuil — aucune action requise.")