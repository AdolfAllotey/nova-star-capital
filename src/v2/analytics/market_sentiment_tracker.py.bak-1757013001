import os
import json
from collections import defaultdict

SENTIMENT_INPUT = "data/v2/social/combined_sentiment.json"
CATEGORY_MAPPING = "data/v2/classification/token_categories.json"
OUTPUT_FILE = "data/v2/sentiment/sector_sentiment.json"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def load_mapping(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def compute_sentiment_by_sector():
    data = load_json(SENTIMENT_INPUT)
    mapping = load_mapping(CATEGORY_MAPPING)

    sectors = defaultdict(list)

    for entry in data:
        symbol = entry.get("symbol", "").upper()
        sentiment = entry.get("sentiment", 0)
        category = mapping.get(symbol)
        if category:
            sectors[category].append(sentiment)

    result = {}
    for cat, sentiments in sectors.items():
        avg = sum(sentiments) / len(sentiments) if sentiments else 0
        result[cat] = {
            "sentiment_avg": round(avg, 3),
            "mentions": len(sentiments)
        }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"✅ Sentiment sectoriel sauvegardé dans : {OUTPUT_FILE}")

if __name__ == "__main__":
    compute_sentiment_by_sector()