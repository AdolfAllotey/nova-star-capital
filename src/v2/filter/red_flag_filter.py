
# src/v2/filters/red_flag_filter.py

import json
import os

BLACKLIST_PATH = "data/v2/filtered/blacklist_tokens.json"
os.makedirs(os.path.dirname(BLACKLIST_PATH), exist_ok=True)

def generate_blacklist(ethical_scores):
    """
    Crée un fichier JSON contenant les tokens à exclure (red flags).

    Args:
        ethical_scores (list): Liste de dicts avec 'token' et 'status'.
    """
    red_tokens = [t["token"] for t in ethical_scores if t.get("status") == "red"]

    with open(BLACKLIST_PATH, "w") as f:
        json.dump(red_tokens, f, indent=4)

    print(f"✅ Fichier blacklist généré avec {len(red_tokens)} tokens dans {BLACKLIST_PATH}")
    return red_tokens

def load_blacklist():
    """
    Charge les tokens blacklistés depuis le fichier.

    Returns:
        list: Liste de tokens blacklistés
    """
    if os.path.exists(BLACKLIST_PATH):
        with open(BLACKLIST_PATH, "r") as f:
            return json.load(f)
    return []

# Exemple de test
if __name__ == "__main__":
    sample_scores = [
        {"token": "BTC", "status": "green"},
        {"token": "ETH", "status": "green"},
        {"token": "RUG", "status": "red"},
        {"token": "SCAM", "status": "red"}
    ]
    generate_blacklist(sample_scores)
    print(load_blacklist())
