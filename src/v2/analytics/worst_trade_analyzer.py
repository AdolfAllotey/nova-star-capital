import os
from datetime import datetime, timezone, timezone
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
    ensure_directory_exists
)
from src.v2.intelligence.llm_analyzer import generate_worst_trades_summary

logger = get_logger("worst_trade_analyzer")

TRADE_SIMULATION_PATH = "src/v2/data/simulation/trade_simulation.json"
WORST_TRADES_PATH = "src/v2/data/risk/worst_trades.json"
BLACKLIST_PATH = "src/v2/data/risk/token_blacklist.json"

def analyze_worst_trades_and_generate_summary():
    logger.info("📉 Analyse des pires trades en cours...")

    trades = load_json_file(TRADE_SIMULATION_PATH)
    if not trades:
        logger.warning("⚠️ Aucun trade simulé trouvé.")
        return

    logger.info(f"📊 Nombre de trades chargés : {len(trades)}")

    # On sélectionne les 3 plus mauvais trades (ici tri aléatoire par date ou montant simulé)
    worst_trades = trades[:3]

    ensure_directory_exists(os.path.dirname(WORST_TRADES_PATH))
    save_json_file(WORST_TRADES_PATH, worst_trades)
    logger.info(f"✅ Rapport des pires trades sauvegardé dans {WORST_TRADES_PATH}")

    # Génération du résumé LLM
    generate_worst_trades_summary(worst_trades)

    # Option : blacklist automatique
    tokens = list(set(trade["token"] for trade in worst_trades))
    blacklist = load_json_file(BLACKLIST_PATH, fallback=[])

    # On ajoute les tokens non déjà blacklistés
    new_blacklist = list(set(blacklist + tokens))
    save_json_file(BLACKLIST_PATH, new_blacklist)
    logger.info(f"🛑 Blacklist mise à jour avec {len(tokens)} tokens : {new_blacklist}")