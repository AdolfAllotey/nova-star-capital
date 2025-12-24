import os
import json

# === Seuils Axiom-like ===
MIN_MARKETCAP = 35_000
MAX_DOMINANT_WALLET = 5.0  # en %
MIN_VOLUME = 10_000
MIN_KOL_MENTIONS = 5

INPUT_FILE = "data/v2/scoring/token_scores.json"
OUTPUT_FILE = "data/v2/scoring/token_filtered.json"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

def load_token_scores(filepath):
    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable : {filepath}")
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def is_green_flag(token):
    try:
        return (
            token.get("marketcap", 0) > MIN_MARKETCAP and
            token.get("dominant_wallet_pct", 100) < MAX_DOMINANT_WALLET and
            token.get("volume", 0) > MIN_VOLUME and
            token.get("kol_mentions", 0) >= MIN_KOL_MENTIONS
        )
    except Exception as e:
        print(f"Erreur sur le token {token.get('symbol', '')} : {e}")
        return False

def filter_tokens(tokens):
    return [token for token in tokens if is_green_flag(token)]

def save_filtered_tokens(tokens, filepath):
    with open(filepath, "w") as f:
        json.dump(tokens, f, indent=2)
    print(f"✅ {len(tokens)} tokens filtrés sauvegardés dans : {filepath}")

def main():
    print("🔍 Filtrage des tokens selon les critères green flags...")
    tokens = load_token_scores(INPUT_FILE)
    filtered = filter_tokens(tokens)
    save_filtered_tokens(filtered, OUTPUT_FILE)

if __name__ == "__main__":
    main()