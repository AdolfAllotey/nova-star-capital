import sys
import os

# Ajout du dossier src à PYTHONPATH (racine du projet)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(root_dir, 'src'))

from social.telegram_scraper import scrape_telegram_messages
from social.reddit_scraper import scrape_reddit_posts

def test_telegram_scraper():
    print("=== Test Telegram Scraper (mock) ===")
    try:
        scrape_telegram_messages()
        print("✅ Telegram scraping mock OK")
    except Exception as e:
        print(f"❌ Erreur Telegram scraper : {e}")

def test_reddit_scraper():
    print("\n=== Test Reddit Scraper ===")
    try:
        scrape_reddit_posts()
        print("✅ Reddit scraping OK")
    except Exception as e:
        print(f"❌ Erreur Reddit scraper : {e}")

if __name__ == "__main__":
    test_telegram_scraper()
    test_reddit_scraper()