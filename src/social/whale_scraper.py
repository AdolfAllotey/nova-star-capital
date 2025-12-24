import os
import pandas as pd
import requests
from dotenv import load_dotenv
import ccxt

# === Chargement ENV ===
load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

if not ETHERSCAN_API_KEY:
    raise ValueError("❌ ETHERSCAN_API_KEY non trouvée dans .env")

# === Constantes ===
ETHERSCAN_BASE_URL = "https://api.etherscan.io/api"
INPUT_CSV = "data/social/whale_addresses.csv"
OUTPUT_CSV = "data/social/whale_transactions.csv"

# === Initialisation Binance
binance = ccxt.binance()
binance.load_markets()
all_symbols = {m.split("/")[0]: m for m in binance.symbols if m.endswith("/USDT")}

def fetch_transactions(address, max_records=10):
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(ETHERSCAN_BASE_URL, params=params)
        data = response.json()

        if data["status"] != "1":
            print(f"⚠️ Aucune transaction trouvée pour {address} ou erreur.")
            return []

        return data["result"][:max_records]

    except Exception as e:
        print(f"❌ Erreur API pour {address} : {e}")
        return []

def extract_token_symbol(tx):
    """Essaye d'extraire un nom de token plausible depuis la transaction"""
    symbol = tx.get("tokenSymbol", "")
    if symbol and symbol.upper() in all_symbols:
        return symbol.upper()
    return None

def run_scraper():
    print("🔍 Chargement des adresses whales...")

    if not os.path.exists(INPUT_CSV):
        print("❌ Fichier whale_addresses.csv introuvable.")
        return

    df = pd.read_csv(INPUT_CSV)
    all_tx = []

    for index, row in df.iterrows():
        name = row.get("name", f"whale_{index}")
        address = row["address"]
        print(f"🔎 Adresse {name} ({address})...")

        txs = fetch_transactions(address)
        for tx in txs:
            token = extract_token_symbol(tx)
            if token:
                tx["token_symbol"] = token
                tx["whale_name"] = name
                all_tx.append(tx)

    if not all_tx:
        print("❌ Aucune transaction avec token symbol valide.")
        return

    tx_df = pd.DataFrame(all_tx)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    tx_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Transactions sauvegardées dans : {OUTPUT_CSV}")

if __name__ == "__main__":
    run_scraper()