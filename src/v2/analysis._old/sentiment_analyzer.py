import os
import statistics
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("sentiment_analyzer")

def analyze_sentiment():
    logger.info("🔍 Analyse du sentiment social")

    # Chargement des fichiers
    telegram_data_path = "src/v2/data/social/telegram_data.json"
    twitter_data_path = "src/v2/data/social/twitter_data.json"
    reddit_data_path = "src/v2/data/social/reddit_data.json"

    telegram_data = load_json_file(telegram_data_path, fallback=[])
    twitter_data = load_json_file(twitter_data_path, fallback=[])
    reddit_data = load_json_file(reddit_data_path, fallback=[])

    # Compatibilité : extraire contenu si le fichier est un dict avec clé unique
    if isinstance(telegram_data, dict) and "messages" in telegram_data:
        telegram_data = telegram_data["messages"]
    if isinstance(twitter_data, dict) and "tweets" in twitter_data:
        twitter_data = twitter_data["tweets"]
    if isinstance(reddit_data, dict) and "posts" in reddit_data:
        reddit_data = reddit_data["posts"]

    messages = telegram_data + twitter_data + reddit_data
    logger.info(f"📊 Nombre total de messages trouvés : {len(messages)}")

    sentiment_scores = []

    for msg in messages:
        text = msg.get("text") if isinstance(msg, dict) else None
        if text and isinstance(text, str):
            score = simple_sentiment_score(text)
            sentiment_scores.append({"text": text, "score": score})

    # Sauvegarde des résultats
    sentiment_file = "src/v2/data/sentiment/sentiment_results.json"
    save_json_file(sentiment_file, sentiment_scores)
    logger.info(f"✅ Fichier généré : {sentiment_file}")

    # Moyenne simple
    if sentiment_scores:
        scores = [s["score"] for s in sentiment_scores]
        average = round(statistics.mean(scores), 4)
    else:
        average = 0.0

    average_file = "src/v2/data/sentiment/average_sentiment.json"
    save_json_file(average_file, {"average_sentiment": average})
    logger.info(f"✅ Score moyen sauvegardé : {average} dans {average_file}")


def simple_sentiment_score(text):
    text = text.lower()
    positive_words = ["buy", "moon", "bull", "up", "gain", "pump", "profit", "good"]
    negative_words = ["sell", "rug", "scam", "bear", "down", "loss", "dump", "bad"]
    
    score = 0
    for word in positive_words:
        if word in text:
            score += 1
    for word in negative_words:
        if word in text:
            score -= 1
    return score


if __name__ == "__main__":
    analyze_sentiment()