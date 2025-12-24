# src/v2/analytics/generate_sentiment_analysis.py

import os
import json
from textblob import TextBlob
from src.v2.utils.file_utils import load_json_file, save_json_file, ensure_folder_exists, get_logger

logger = get_logger("generate_sentiment_analysis")

def analyze_sentiment(text):
    try:
        analysis = TextBlob(text)
        return analysis.sentiment.polarity  # entre -1 et 1
    except Exception as e:
        logger.warning(f"Erreur lors de l’analyse de sentiment : {e}")
        return 0.0

def generate_sentiment_analysis():
    logger.info("🔍 Début de l'analyse du sentiment")

    telegram_data_path = "src/v2/data/social/telegram_data.json"
    twitter_data_path = "src/v2/data/social/twitter_data.json"
    reddit_data_path = "src/v2/data/social/reddit_data.json"
    output_path = "src/v2/data/sentiment/sentiment_results.json"

    all_messages = []

    for path in [telegram_data_path, twitter_data_path, reddit_data_path]:
        data = load_json_file(path, fallback=[])
        if isinstance(data, list):
            messages = [d.get("text", "") for d in data if isinstance(d, dict)]
            all_messages.extend(messages)
        else:
            logger.warning(f"Format inattendu dans {path}")

    if not all_messages:
        logger.warning("Aucun message trouvé pour l’analyse du sentiment.")
        save_json_file(output_path, {"average_sentiment": 0.0, "message_count": 0})
        return

    sentiments = [analyze_sentiment(msg) for msg in all_messages if msg.strip()]

    average_sentiment = round(sum(sentiments) / len(sentiments), 4) if sentiments else 0.0

    result = {
        "average_sentiment": average_sentiment,
        "message_count": len(sentiments)
    }

    ensure_folder_exists(os.path.dirname(output_path))
    save_json_file(output_path, result)

    logger.info(f"✅ Analyse du sentiment terminée. Moyenne : {average_sentiment} sur {len(sentiments)} messages.")