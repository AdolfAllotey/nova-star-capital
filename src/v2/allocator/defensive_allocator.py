
import os
import json
from datetime import datetime, timezone, timezone
from utils.telegram_bot import send_telegram_message

EXTRACTED_FILE = "data/v2/performance/profit_extracted.json"
ALLOCATED_FILE = "data/v2/performance/defensive_allocation_log.json"

os.makedirs(os.path.dirname(ALLOCATED_FILE), exist_ok=True)

def allocate_defensively(destination="sous-compte_sécurité"):
    """
    Répartit le montant extrait dans un compartiment défensif (ex: USDT, stablecoins, ETF via IBKR...).

    Args:
        destination (str): Destination de l’allocation (nom du sous-compte ou type d’actif)

    Returns:
        dict: Détail de l’opération
    """
    if not os.path.exists(EXTRACTED_FILE):
        print("❌ Aucun profit à sécuriser.")
        return None

    with open(EXTRACTED_FILE, "r") as f:
        data = json.load(f)

    amount = data.get("extracted_amount", 0)
    if amount <= 0:
        print("❌ Montant extrait nul.")
        return None

    allocation = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "amount": amount,
        "destination": destination
    }

    with open(ALLOCATED_FILE, "a") as f:
        f.write(json.dumps(allocation) + "\n")

    message = f"🛡️ {amount} € de gains ont été alloués au portefeuille défensif ({destination})."
    send_telegram_message(message)
    print(message)

    return allocation

# Test
if __name__ == "__main__":
    allocate_defensively()
