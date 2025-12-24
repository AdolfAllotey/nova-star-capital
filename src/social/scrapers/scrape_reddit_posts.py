import os
import pandas as pd
import datetime
import praw

def scrape_reddit_posts():
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )

    subreddits = ["cryptomoonshots", "Altcoin", "CryptoCurrency"]
    all_posts = []

    for sub in subreddits:
        print(f"📡 Scraping subreddit: {sub}")
        try:
            for post in reddit.subreddit(sub).hot(limit=100):
                all_posts.append({
                    "title": post.title,
                    "body": post.selftext,
                    "created_utc": post.created_utc,
                    "subreddit": sub,
                    "score": post.score,
                    "text": f"{post.title} {post.selftext}"
                })
        except Exception as e:
            print(f"❌ Erreur scraping {sub}: {e}")

    df = pd.DataFrame(all_posts)
    if df.empty:
        print("⚠️ Aucun post Reddit récupéré.")
        return pd.DataFrame()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"data/social/reddit_posts_{timestamp}.csv"
    latest_path = "data/social/reddit_posts_latest.csv"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    if os.path.islink(latest_path) or os.path.exists(latest_path):
        os.remove(latest_path)
    os.symlink(os.path.basename(output_path), latest_path)

    print(f"✅ {len(df)} posts enregistrés dans {output_path}")
    return df