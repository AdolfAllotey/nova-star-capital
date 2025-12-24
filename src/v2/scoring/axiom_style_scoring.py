import os
import json

INPUT_FILE = "data/v2/scoring/token_scores.json"
WHALES_FILE = "data/v2/whales/whale_tokens.json"
KOLS_FILE = "data/v2/kol_tracking/kol_signals.json"
GREEN_FILE = "data/v2/scoring/token_filtered.json"
SNIPER_FILE = "data/v2/sniper/sniper_detected.json"
OUTPUT_FILE = "data/v2/scoring/enriched_scores.json"

WEIGHTS = {
    "base_score": 0.5,
    "whale": 0.2,
    "kol": 0.2,
    "green": 0.05,
    "sniper": 0.05,
}

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def enrich_scores():
    base_tokens = load_json(INPUT_FILE)
    whales = load_json(WHALES_FILE)
    kols = load_json(KOLS_FILE)
    green_flags = load_json(GREEN_FILE)
    sniper = load_json(SNIPER_FILE)

    whale_symbols = {t["symbol"].upper() for t in whales}
    kol_map = {t["symbol"].upper(): t.get("mentions", 0) for t in kols}
    green_symbols = {t["symbol"].upper() for t in green_flags}
    sniper_symbols = {t["baseToken"]["symbol"].upper() for t in sniper}

    enriched = []

    for token in base_tokens:
        symbol = token.get("symbol", "").upper()
        base_score = token.get("score", 0)

        is_whale = symbol in whale_symbols
        kol_mentions = kol_map.get(symbol, 0)
        is_green = symbol in green_symbols
        is_sniper = symbol in sniper_symbols

        final_score = (
            WEIGHTS["base_score"] * base_score +
            WEIGHTS["whale"] * (100 if is_whale else 0) +
            WEIGHTS["kol"] * min(kol_mentions * 10, 100) +
            WEIGHTS["green"] * (100 if is_green else 0) +
            WEIGHTS["sniper"] * (100 if is_sniper else 0)
        )

        token.update({
            "whale_detected": is_whale,
            "kol_mentions": kol_mentions,
            "green_flag": is_green,
            "sniper_flag": is_sniper,
            "score_enriched": round(final_score, 2)
        })

        enriched.append(token)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"✅ Enriched scores sauvegardés dans : {OUTPUT_FILE}")

if __name__ == "__main__":
    enrich_scores()