import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement depuis twitter.env
load_dotenv(dotenv_path=".env/twitter.env")

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "User-Agent": "BotCryptoUltraTwitterScraper"
}

QUERY = "crypto OR altcoin OR pepe OR shiba OR shitcoin OR binance"
SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

def scrape_twitter_posts(limit=100):
    if not BEARER_TOKEN:
        print("❌ BEARER_TOKEN non défini.")
        return pd.DataFrame()

    print("📡 Scraping Twitter avec l'API officielle...")

    params = {
        "query": QUERY,
        "max_results": min(limit, 100),  # Twitter limite à 100 par requête
        "tweet.fields": "created_at,text,author_id",
    }

    response = requests.get(SEARCH_URL, headers=HEADERS, params=params)

    if response.status_code != 200:
        print(f"❌ Erreur Twitter API : {response.status_code} - {response.text}")
        return pd.DataFrame()

    data = response.json().get("data", [])
    print(f"✅ {len(data)} tweets récupérés")

    rows = [{
        "title": tweet["text"],
        "link": f"https://twitter.com/i/web/status/{tweet['id']}",
        "score": 1,  # Score par défaut, à ajuster plus tard
        "source": "twitter"
    } for tweet in data]

    df = pd.DataFrame(rows)
    return df

# Pour test manuel :
if __name__ == "__main__":
    df = scrape_twitter_posts()
    print(df.head())