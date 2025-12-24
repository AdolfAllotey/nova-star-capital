import os
import pandas as pd
from datetime import datetime
import praw
from dotenv import load_dotenv

# === ENV ===
load_dotenv()
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "crypto_bot")

# === PATHS ===
OUTPUT_DIR = "data/social"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def scrape_reddit_posts(subreddits=None, limit=200):
    if subreddits is None:
        subreddits = ["CryptoCurrency", "CryptoMoonShots", "Altcoin", "Binance", "ethtrader"]

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

    posts = []
    for sub in subreddits:
        subreddit = reddit.subreddit(sub)
        for post in subreddit.new(limit=limit):
            posts.append({
                "subreddit": sub,
                "title": post.title,
                "text": post.selftext,
                "created": datetime.fromtimestamp(post.created_utc),
                "url": post.url,
                "score": post.score
            })

    df = pd.DataFrame(posts)
    filename = f"reddit_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False)
    latest_path = os.path.join(OUTPUT_DIR, "reddit_posts_latest.csv")
    df.to_csv(latest_path, index=False)
    print(f"✅ {len(df)} posts sauvegardés.")

def extract_reddit_tokens(csv_path="data/social/reddit_posts_latest.csv"):
    try:
        df = pd.read_csv(csv_path)
        tokens = []
        for _, row in df.iterrows():
            for field in ["title", "text"]:
                msg = row.get(field)
                if isinstance(msg, str):
                    tokens += [word for word in msg.split() if word.startswith("$") and len(word) > 1]
        return list(set(tokens))
    except Exception as e:
        print(f"❌ Erreur extraction Reddit : {e}")
        return []

__all__ = ["scrape_reddit_posts", "extract_reddit_tokens"]