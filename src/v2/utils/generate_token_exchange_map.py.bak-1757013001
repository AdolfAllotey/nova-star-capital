import os
import json
from src.v2.utils.file_utils import load_selected_tokens, save_json_file
from src.v2.utils.logger import get_logger

logger = get_logger("generate_token_exchange_map")

def generate_token_exchange_map():
    logger.info("🗺️ Génération de token_exchange_map.json...")
    
    try:
        tokens = load_selected_tokens()
        if not tokens:
            logger.warning("⚠️ Aucun token sélectionné.")
            return

        # Attribution par défaut à Binance (logique simple à affiner plus tard)
        exchange_map = {token: "binance" for token in tokens}

        # Exemple : attribuer certains tokens à MEXC si souhaité
        for token in tokens:
            if token.lower() not in ["bitcoin", "ethereum", "solana"]:
                exchange_map[token] = "mexc"

        output_path = "src/v2/data/token_exchange_map.json"
        save_json_file(output_path, exchange_map)
        logger.info(f"✅ Fichier généré : {output_path}")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération : {e}", exc_info=True)

if __name__ == "__main__":
    generate_token_exchange_map()