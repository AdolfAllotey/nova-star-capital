import json
import os
from datetime import datetime, timezone, timezone

def load_scores(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        return json.load(f)

def combine_scores(sentiment_scores, fundamental_scores, technical_scores, weight_sentiment=1, weight_fundamental=1, weight_technical=1):
    combined_scores = {}

    all_tokens = set(sentiment_scores) | set(fundamental_scores) | set(technical_scores)

    for token in all_tokens:
        sentiment = sentiment_scores.get(token, 0)
        fundamental = fundamental_scores.get(token, 0)
        technical = technical_scores.get(token, 0)

        weighted_sum = (sentiment * weight_sentiment +
                        fundamental * weight_fundamental +
                        technical * weight_technical)
        total_weight = weight_sentiment + weight_fundamental + weight_technical

        combined_score = weighted_sum / total_weight
        combined_scores[token] = round(combined_score, 4)

    return combined_scores

def save_combined_scores(combined_scores, folder="src/v2/data/scores/"):
    os.makedirs(folder, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = os.path.join(folder, f"combined_scores_{date_str}.json")
    with open(output_path, "w") as f:
        json.dump(combined_scores, f, indent=4)
    print(f"✅ Combined scores saved to {output_path}")

if __name__ == "__main__":
    sentiment_path = "src/v2/data/scores/sentiment_scores.json"
    fundamental_path = "src/v2/data/scores/fundamental_scores.json"
    technical_path = "src/v2/data/scores/technical_scores.json"

    sentiment_scores = load_scores(sentiment_path)
    fundamental_scores = load_scores(fundamental_path)
    technical_scores = load_scores(technical_path)

    combined = combine_scores(sentiment_scores, fundamental_scores, technical_scores)
    save_combined_scores(combined)