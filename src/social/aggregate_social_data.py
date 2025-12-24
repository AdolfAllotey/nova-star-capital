import os
import pandas as pd
from datetime import datetime

DATA_DIR = "data/social"
TELEGRAM_FILE = os.path.join(DATA_DIR, "telegram_posts.csv")
REDDIT_FILE = os.path.join(DATA_DIR, "reddit_posts.csv")
TWITTER_FILE = os.path.join(DATA_DIR, "twitter_posts.csv")

def load_data(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()

def main():
    print("📄 Chargement des données Telegram...")
    df_telegram = load_data(TELEGRAM_FILE)
    df_telegram["source"] = "telegram"

    print("📄 Chargement des données Reddit...")
    df_reddit = load_data(REDDIT_FILE)
    df_reddit["source"] = "reddit"

    print("📄 Chargement des données Twitter...")
    df_twitter = load_data(TWITTER_FILE)
    df_twitter["source"] = "twitter"

    df_all = pd.concat([df_telegram, df_reddit, df_twitter], ignore_index=True)
    df_all = df_all[["title", "link", "score", "source"]].dropna(subset=["title"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(DATA_DIR, f"social_aggregated_{timestamp}.csv")
    latest_link = os.path.join(DATA_DIR, "social_aggregated_latest.csv")

    df_all.to_csv(output_file, index=False)
    if os.path.exists(latest_link):
        os.remove(latest_link)
    os.symlink(os.path.basename(output_file), latest_link)

    print(f"✅ Données agrégées sauvegardées dans {latest_link} ({len(df_all)} lignes)")

if __name__ == "__main__":
    main()