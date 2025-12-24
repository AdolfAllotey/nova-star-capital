import os
import json
from datetime import datetime, timezone, timezone
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json, save_json

logger = get_logger("portfolio_tracker")

FINAL_SCORES_PATH = "src/v2/data/scores/final_scores.json"
OUTPUT_PATH = "src/v2/data/scores/global_performance.json"

# Répartition fictive des symboles par sous-compte (exemple)
ACCOUNT_MAPPING = {
    "trading": ["BTC", "ETH", "SOL", "DOGE"],
    "securite": ["USDC", "DAI"],
    "bfr": ["LDO", "AAVE"],
    "entreprise": ["MKR"]
}

def get_subaccount(symbol):
    for account, tokens in ACCOUNT_MAPPING.items():
        if symbol.upper() in tokens:
            return account
    return "trading"  # par défaut

def load_final_scores():
    try:
        return load_json(FINAL_SCORES_PATH)
    except Exception as e:
        logger.error(f"Erreur lecture des scores : {e}")
        return []

def track_portfolio():
    logger.info("Suivi des performances portefeuille...")
    scores = load_final_scores()

    result = {}
    for token in scores:
        account = get_subaccount(token["symbol"])
        gain = token.get("simulated_gain_eur", 0)

        if account not in result:
            result[account] = {"total_gain_eur": 0, "tokens": 0}

        result[account]["total_gain_eur"] += gain
        result[account]["tokens"] += 1

    # Conversion en pourcentage (à partir d’un capital initial fictif de 2500€/sous-compte)
    for account, data in result.items():
        initial = 2500
        data["performance_percent"] = round(100 * data["total_gain_eur"] / initial, 2)

    final_report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "subaccounts": result
    }

    save_json(final_report, OUTPUT_PATH)
    logger.info(f"Fichier global sauvegardé : {OUTPUT_PATH}")

if __name__ == "__main__":
    track_portfolio()