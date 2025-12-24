import os
from dotenv import load_dotenv

# Charger les variables d'environnement Twitter
load_dotenv(dotenv_path="twitter.env")
twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

from social.scrapers.scrape_telegram_groups import update_telegram_group_list
from social.scrape_social_data import run_social_scraping
from social.detect_tokens_from_social import detect_tokens_from_texts
from social.score_tokens import score_detected_tokens
from social.analyze_social_sentiment import analyze_social_sentiment

def main():
    print("🚀 Lancement du scraping global...\n")

    # Étape 1 - Scraping Telegram
    update_telegram_group_list()

    # Étape 2 - Scraping Twitter, Reddit...
    run_social_scraping(twitter_bearer_token=twitter_bearer_token)

    # Étape 3 - Détection de tokens
    detect_tokens_from_texts()

    # Étape 4 - Scoring des tokens
    score_detected_tokens()

    # Étape 5 - Analyse de sentiment
    analyze_social_sentiment()

if __name__ == "__main__":
    main()