import os
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import datetime

# 📦 Chargement du fichier .env
env_path = os.environ.get("ENV_PATH", ".env.twitter")
load_dotenv(dotenv_path=env_path)

bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

if not bearer_token:
    raise ValueError("🔐 Twitter bearer token is missing. Check your .env.twitter file.")

headers = {"Authorization": f"Bearer {bearer_token}"}
query = "crypto OR altcoin OR pepe OR shiba OR shitcoin OR binance"
url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&tweet.fields=public_metrics&max_results=100"

response = requests.get(url, headers=headers)

if response.status_code != 200:
    raise Exception(f"❌ Erreur requête Twitter : {response.status_code} - {response.text}")

tweets = response.json().get("data", [])

data = []
for tweet in tweets:
    data.append({
        "title": tweet.get("text"),
        "link": f"https://twitter.com/i/web/status/{tweet.get('id')}",
        "score": tweet.get("public_metrics", {}).get("retweet_count", 0),
        "source": "twitter"
    })

df = pd.DataFrame(data)
output_path = f"data/social/twitter_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
df.to_csv(output_path, index=False)
print(f"✅ {len(df)} tweets enregistrés dans {output_path}")