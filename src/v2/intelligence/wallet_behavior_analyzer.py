# src/v2/intelligence/wallet_behavior_analyzer.py

import os
import json
import time
import requests
from datetime import datetime, timezone, timezone
from dotenv import load_dotenv
from src.v2.utils.logger import get_logger

load_dotenv()
logger = get_logger("wallet_behavior_analyzer")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
CHAIN_ID = 1  # Ethereum Mainnet
BASE_URL = f"https://api.etherscan.io/api"

OUTPUT_DIR = "src/v2/data/intelligence/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_wallet_transactions(address, start_block=0, end_block=99999999):
    url = (
        f"{BASE_URL}?module=account"
        f"&action=txlist"
        f"&address={address}"
        f"&startblock={start_block}"
        f"&endblock={end_block}"
        f"&sort=asc"
        f"&apikey={ETHERSCAN_API_KEY}"
        f"&chainid={CHAIN_ID}"
    )

    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] != "1":
            logger.warning(f"Erreur Etherscan pour {address} : {data.get('message')}")
            return []
        return data["result"]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transactions : {e}")
        return []

def analyze_wallet_behavior(address):
    transactions = get_wallet_transactions(address)
    if not transactions:
        return None

    hold_durations = []
    trade_volumes = []
    last_timestamp = None
    trade_count = 0

    for tx in transactions:
        if tx["to"].lower() == address.lower():
            continue  # Skip incoming transactions
        try:
            timestamp = int(tx["timeStamp"])
            value = int(tx["value"]) / 1e18  # Convert from Wei to ETH

            if last_timestamp:
                duration = timestamp - last_timestamp
                hold_durations.append(duration)

            trade_volumes.append(value)
            last_timestamp = timestamp
            trade_count += 1
        except Exception as e:
            logger.warning(f"Erreur parsing tx : {e}")
            continue

    if trade_count == 0:
        return None

    avg_hold = sum(hold_durations) / len(hold_durations) if hold_durations else 0
    avg_volume = sum(trade_volumes) / len(trade_volumes)
    frequency = trade_count / (max(hold_durations) / 86400) if hold_durations else 0

    result = {
        "address": address,
        "trades": trade_count,
        "avg_hold_duration_days": round(avg_hold / 86400, 2),
        "avg_volume_eth": round(avg_volume, 4),
        "trade_frequency_per_day": round(frequency, 2),
    }
    return result

def save_wallet_analysis(data):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{OUTPUT_DIR}wallet_analysis_{data['address']}_{ts}.json"
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Analyse enregistrée : {filename}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde : {e}")

if __name__ == "__main__":
    # Exemple : remplace cette adresse par celle que tu veux analyser
    wallet_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    result = analyze_wallet_behavior(wallet_address)
    if result:
        save_wallet_analysis(result)
    else:
        logger.warning("Aucune donnée analysable pour ce wallet.")