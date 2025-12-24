import json
import os
from src.v2.intelligence.whale_behavior_analyzer import analyze_batch
from src.v2.utils.logger import get_logger

logger = get_logger("run_whale_analysis")

WALLETS_PATH = "src/v2/data/intelligence/wallets_to_analyze.json"
OUTPUT_PATH = "src/v2/data/intelligence/whale_behavior.json"

def load_wallets():
    if not os.path.exists(WALLETS_PATH):
        logger.error("❌ Fichier wallets_to_analyze.json introuvable.")
        return []
    with open(WALLETS_PATH, "r") as f:
        return json.load(f)

def save_results(results):
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"✅ Résultats enregistrés dans {OUTPUT_PATH}")

def main():
    logger.info("📊 Lancement de l’analyse des whales")
    wallets = load_wallets()
    if not wallets:
        logger.warning("🚫 Aucun wallet à analyser.")
        return
    results = analyze_batch(wallets)
    save_results(results)

if __name__ == "__main__":
    main()