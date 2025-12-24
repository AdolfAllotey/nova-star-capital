import os
import json
from dotenv import load_dotenv

from src.v2.utils.logger import get_logger
from src.v2.core.retry_manager import retry_on_failure

load_dotenv()
logger = get_logger("risk_controller")

BLACKLIST_FILE = "src/v2/data/risk/token_blacklist.json"
RISK_POLICY_FILE = "src/v2/config/risk_policy.json"  # optionnel

# Valeurs par défaut
DEFAULT_MAX_EXPOSURE_PERCENT = 10
DEFAULT_DRAWNDOWN_LIMIT = -25  # en %


def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r") as f:
        return json.load(f)


def load_risk_policy():
    if not os.path.exists(RISK_POLICY_FILE):
        return {
            "max_token_exposure_percent": DEFAULT_MAX_EXPOSURE_PERCENT,
            "max_drawdown_percent": DEFAULT_DRAWNDOWN_LIMIT
        }
    with open(RISK_POLICY_FILE, "r") as f:
        return json.load(f)


@retry_on_failure(retries=3, delay=5, alert_name="risk_controller_check")
def is_token_risky(token_symbol: str, current_exposure_percent: float, global_drawdown_percent: float) -> bool:
    """
    Vérifie si un token est risqué selon plusieurs règles :
    - présence dans la blacklist
    - dépassement de l’exposition maximale
    - drawdown global trop élevé
    """
    blacklist = load_blacklist()
    risk_policy = load_risk_policy()

    if token_symbol.lower() in [t.lower() for t in blacklist]:
        logger.warning(f"{token_symbol} est dans la blacklist.")
        return True

    if current_exposure_percent > risk_policy["max_token_exposure_percent"]:
        logger.warning(f"{token_symbol} dépasse le seuil d'exposition autorisé ({current_exposure_percent}%).")
        return True

    if global_drawdown_percent < risk_policy["max_drawdown_percent"]:
        logger.warning(f"Drawdown global trop élevé : {global_drawdown_percent}%. Trade bloqué.")
        return True

    return False


if __name__ == "__main__":
    # Exemple d'appel
    risky = is_token_risky("XYZ", current_exposure_percent=12, global_drawdown_percent=-18)
    print("Risque détecté :", risky)