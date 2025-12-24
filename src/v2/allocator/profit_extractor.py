
import json
import os
from datetime import datetime, timezone, timezone

LOG_FILE = "data/v2/performance/cumulative_profit.json"
EXTRACTED_FILE = "data/v2/performance/profit_extracted.json"
THRESHOLD = 300  # Exemple : extraction déclenchée au-delà de 300€ de gain

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def extract_profits(threshold=THRESHOLD, save=True):
    """
    Vérifie les gains cumulés et extrait la part à sécuriser si le seuil est dépassé.

    Args:
        threshold (float): Seuil déclencheur
        save (bool): Enregistre le résultat

    Returns:
        float: Montant extrait pour sécurisation
    """
    if not os.path.exists(LOG_FILE):
        print("📭 Aucune donnée de profit trouvée.")
        return 0.0

    with open(LOG_FILE, "r") as f:
        perf = json.load(f)
        total_profit = perf.get("cumulative_pnl", 0)

    if total_profit <= threshold:
        return 0.0

    # Exemple : on sécurise 25% de l'excédent
    amount_to_extract = round((total_profit - threshold) * 0.25, 2)

    if save:
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "extracted_amount": amount_to_extract,
            "total_profit": total_profit
        }
        with open(EXTRACTED_FILE, "w") as f:
            json.dump(result, f, indent=2)

    print(f"🔐 Profit extrait : {amount_to_extract} €")
    return amount_to_extract

# Test
if __name__ == "__main__":
    extract_profits()
