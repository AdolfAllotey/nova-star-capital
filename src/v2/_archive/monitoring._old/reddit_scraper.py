import os
import json
from datetime import datetime, timezone, timezone
from dotenv import load_dotenv

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import save_json_file, ensure_directory_exists

# Configuration
DATA_PATH = "src/v2/data/social/reddit_data.json"
logger = get_logger("reddit_scraper")

load_dotenv()
ensure_directory_exists(os.path.dirname(DATA_PATH))

def scrape_reddit():
    logger.info("🚀 Démarrage du scraping Reddit (simulé)")

    # ⚠️ Exemple fictif, remplacer par une vraie API plus tard
    data = [
        {
            "subreddit": "CryptoCurrency",
            "title": "Huge pump incoming for $PEPE",
            "text": "Whales accumulating again...",
            "date": datetime.now(timezone.utc).isoformat()
        },
        {
            "subreddit": "CryptoMoonShots",
            "title": "New gem spotted 🚀",
            "text": "Check out this low market cap token!",
            "date": datetime.now(timezone.utc).isoformat()
        }
    ]

    save_json_file(DATA_PATH, data)
    logger.info(f"✅ {len(data)} posts Reddit enregistrés dans {DATA_PATH}")