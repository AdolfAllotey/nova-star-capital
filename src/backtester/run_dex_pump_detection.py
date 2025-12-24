import os
import json
import requests
import pandas as pd
from datetime import datetime

# === Paramètres de détection ===
SEARCH_TERMS = ["usdt", "pepe", "moon", "doge", "arb", "sol", "pump"]
MIN_CHANGE_1H = 10.0       # % minimum de variation en 1h
MIN_VOLUME_24H = 50000.0   # Volume 24h minimum
TOP_N_RESULTS = 30         # Nombre de résultats à analyser par recherche

OUTPUT_PATH = "data/social/dex_pumped_tokens.csv"
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

def fetch_pairs_for_term(term):
    url = f"https://api.dexscreener.com/latest/dex/search/?q={term}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get("pairs", [])[:TOP_N_RESULTS]
        return data
    except Exception as e:
        print(f"❌ Erreur DEXScreener ({term}) : {e}")
        return []

def is_valid_pair(pair):
    try:
        change_1h = float(pair.get("priceChange", {}).get("h1", "0") or 0)
        volume_24h = float(pair.get("volume", {}).get("h24", "0") or 0)
        return change_1h >= MIN_CHANGE_1H and volume_24h >= MIN_VOLUME_24H
    except:
        return False

def detect_pumps():
    print("🚀 Lancement de la détection de pumps DEX...")

    pumped = []

    for term in SEARCH_TERMS:
        print(f"🔍 Recherche via DEXScreener : {term}")
        pairs = fetch_pairs_for_term(term)

        if not pairs:
            print(f"⚠️ Aucun résultat pour {term}")
            continue

        print(f"📊 {len(pairs)} paires trouvées. Exemple :")
        for p in pairs[:5]:
            base = p.get("baseToken", {}).get("symbol", "N/A")
            quote = p.get("quoteToken", {}).get("symbol", "N/A")
            change = p.get("priceChange", {}).get("h1", None)
            vol = p.get("volume", {}).get("h24", None)
            tx = p.get("txCount", {}).get("h24", None)
            print(f"- {base} / {quote} | 1h: {change}% | Vol 24h: ${vol} | Tx: {tx}")

        for p in pairs:
            if is_valid_pair(p):
                pumped.append({
                    "base": p["baseToken"]["symbol"],
                    "quote": p["quoteToken"]["symbol"],
                    "dex": p.get("dexId", ""),
                    "pair_address": p.get("pairAddress", ""),
                    "price": p.get("priceUsd", ""),
                    "change_1h": float(p["priceChange"]["h1"]),
                    "volume_24h": float(p["volume"]["h24"]),
                    "timestamp": datetime.utcnow().isoformat()
                })

    if pumped:
        df = pd.DataFrame(pumped)
        df.to_csv(OUTPUT_PATH, index=False)
        print(f"✅ {len(df)} pump(s) détecté(s) et sauvegardé(s) dans {OUTPUT_PATH}")
    else:
        print("⚠️ Aucun pump détecté avec les critères actuels.")

if __name__ == "__main__":
    detect_pumps()