import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# === CONFIG ===
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/pairs"
CHAIN = "ethereum"  # Exemple : ethereum, bsc, polygon, etc.
MIN_VOLUME_USD = 100000  # Volume minimal
VOLUME_PUMP_THRESHOLD = 3.0  # x3 ou plus

# === Récupère les paires de la chaîne choisie
def fetch_dex_data(chain=CHAIN):
    url = f"{DEXSCREENER_API}/{chain}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("pairs", [])
    except Exception as e:
        print(f"❌ Erreur DEXScreener : {e}")
        return []

# === Filtre les tokens avec un pump de volume
def detect_volume_pumps(pairs, threshold=VOLUME_PUMP_THRESHOLD, min_volume=MIN_VOLUME_USD):
    results = []
    for pair in pairs:
        try:
            volume_24h = float(pair["volume"]["h24"])
            volume_6h = float(pair["volume"]["h6"])
            if volume_6h == 0 or volume_24h < min_volume:
                continue
            ratio = volume_6h / (volume_24h / 4)  # Si 6h représente +x par rapport à 24h / 4
            if ratio >= threshold:
                results.append({
                    "pair": pair.get("pairCreatedAt"),
                    "symbol": pair.get("baseToken", {}).get("symbol"),
                    "volume_6h": volume_6h,
                    "volume_24h": volume_24h,
                    "dex": pair.get("dexId"),
                    "url": pair.get("url"),
                    "pump_ratio": round(ratio, 2)
                })
        except Exception:
            continue
    return results

# === Routine principale
def run_pump_detection():
    print("🔍 Détection de pump sur DEX en cours...")
    pairs = fetch_dex_data()
    pumped = detect_volume_pumps(pairs)
    if not pumped:
        print("⚠️ Aucun pump détecté.")
        return

    df = pd.DataFrame(pumped)
    output_path = f"data/social/dex_pumps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ {len(df)} pump(s) détecté(s) et sauvegardé(s) dans {output_path}")

if __name__ == "__main__":
    run_pump_detection()