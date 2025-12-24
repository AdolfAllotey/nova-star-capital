import json
import os
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.llm_utils import analyze_sentiment_with_openai

logger = get_logger("analyze_sentiment")

DATA_PATH = "src/v2/data/social/social_messages.json"
OUTPUT_PATH = "src/v2/data/social/social_sentiment.json"

def analyze_social_sentiment():
    try:
        logger.info("🔍 Chargement des messages sociaux...")
        messages = load_json_file(DATA_PATH)

        if not messages:
            logger.warning("Aucun message à analyser. Fichier vide ou introuvable.")
            return

        logger.info(f"✅ {len(messages)} messages chargés.")

        logger.info("🧠 Analyse du sentiment avec LLM en cours...")
        sentiment_results = analyze_sentiment_with_openai(messages)

        logger.info("💾 Sauvegarde des résultats de sentiment...")
        save_json_file(sentiment_results, OUTPUT_PATH)

        logger.info(f"✅ Sentiment analysis completed. Output saved to {OUTPUT_PATH}")

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du sentiment : {e}", exc_info=True)