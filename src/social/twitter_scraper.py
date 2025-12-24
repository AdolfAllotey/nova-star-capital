import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import snscrape.modules.twitter as sntwitter
import pandas as pd
import datetime
from utils.token_utils import extract_and_clean_tokens
from utils.file_utils import save_dataframe_with_timestamp

def fetch_tweets(query="crypto OR altcoin OR pepe OR shiba OR shitcoin OR binance", limit=100):
    tweets = []
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
        if i >= limit:
            break
        tweets.append({
            'date': tweet.date,
            'content': tweet.content,
            'username': tweet.user.username,
            'url': tweet.url
        })
    return tweets

def detect_trending_tokens():
    print("🔍 Scraping Twitter pour tokens tendance...")
    try:
        tweets = fetch_tweets()
        df = pd.DataFrame(tweets)
        if df.empty:
            print("❌ Aucun tweet récupéré.")
            return

        all_tokens = extract_and_clean_tokens(df['content'])
        token_counts = pd.Series(all_tokens).value_counts().reset_index()
        token_counts.columns = ['token', 'count']
        token_counts['date'] = datetime.datetime.now()

        save_dataframe_with_timestamp(token_counts, prefix="twitter_tokens", folder="data/social", latest_symlink=True)
        print(f"✅ Données sauvegardées dans data/social")
    except Exception as e:
        print(f"❌ Erreur récupération Twitter : {e}")