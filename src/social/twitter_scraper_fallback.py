import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

QUERY = "crypto OR altcoin OR pepe OR shiba OR shitcoin OR binance"
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.cz",
    "https://nitter.privacy.com.de"
]
DATA_DIR = "data/social"
os.makedirs(DATA_DIR, exist_ok=True)

def parse_nitter_html(html):
    soup = BeautifulSoup(html, "html.parser")
    tweets = soup.select("div.timeline-item > div.tweet-content")
    return [t.get_text(strip=True) for t in tweets]

def get_tweets_from_nitter(query, max_results=50):
    for instance in NITTER_INSTANCES:
        try:
            print(f"\U0001F310 Tentative Nitter : {instance}/search?q={query}")
            url = f"{instance}/search?f=tweets&q={query}&since=&until=&lang=en"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                tweets = parse_nitter_html(response.text)
                if tweets:
                    return tweets[:max_results]
        except Exception as e:
            print(f"⚠️ Erreur Nitter ({instance}): {e}")
        time.sleep(1)
    return []

def main():
    print("\U0001F50D Scraping via Nitter fallback...")
    tweets = get_tweets_from_nitter(QUERY)
    print(f"✅ {len(tweets)} tweets récupérés via fallback")

    tokens = []
    for tweet in tweets:
        words = [w for w in tweet.upper().split() if 2 <= len(w) <= 10 and w.isalnum() and w.isupper()]
        tokens.extend(words)

    tokens = list(pd.Series(tokens).drop_duplicates())
    print(f"\U0001F9F9 {len(tokens)} tokens candidats extraits via fallback : {tokens[:10]}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"{DATA_DIR}/twitter_fallback_tokens_{timestamp}.csv"
    pd.DataFrame({"token": tokens}).to_csv(out_path, index=False)
    print(f"📁 Tokens fallback enregistrés dans {out_path}")

    return tokens

if __name__ == "__main__":
    main()
