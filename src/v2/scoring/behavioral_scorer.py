
# src/v2/scoring/behavioral_scorer.py

import json
import os

SAMPLE_PATH = "src/v2/data/selection/selected_tokens.json"
OUTPUT_PATH = "src/v2/data/scores/behavioral_scores.json"
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

def compute_behavioral_score(token):
    score = 100

    if token.get("top_holder_pct", 100) > 5:
        score -= 30

    if not token.get("audit_passed", False):
        score -= 20

    if token.get("burn_pct", 0) < 1:
        score -= 10

    if not token.get("docs", False):
        score -= 10

    if token.get("dev_wallet_behavior", "") == "frequent_sell":
        score -= 30

    return max(score, 0)

def score_tokens_behaviorally(input_path=SAMPLE_PATH, output_path=OUTPUT_PATH):
    if not os.path.exists(input_path):
        print("❌ Fichier de tokens sélectionnés introuvable.")
        return []

    with open(input_path, "r") as f:
        tokens = json.load(f)

    results = []
    for token in tokens:
        score = compute_behavioral_score(token)
        token_result = {
            "symbol": token.get("symbol", "N/A"),
            "behavioral_score": score
        }
        results.append(token_result)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)

    print(f"✅ Scores comportementaux enregistrés dans {output_path}")
    return results

if __name__ == "__main__":
    score_tokens_behaviorally()
