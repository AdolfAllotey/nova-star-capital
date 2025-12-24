import requests
import os
import json
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path="src/v2/.env")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
if not ETHERSCAN_API_KEY:
    raise ValueError("ETHERSCAN_API_KEY non défini dans src/v2/.env")

processed_txs = set()

def get_wallet_transactions(address, start_block=0, end_block=99999999):
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": start_block,
        "endblock": end_block,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data["status"] == "1":
        return data["result"]
    else:
        print(f"Erreur Etherscan : {data.get('message')}")
        return []

def process_transactions(txs):
    new_trades = []
    for tx in txs:
        tx_hash = tx["hash"]
        if tx_hash in processed_txs:
            continue  # déjà traité

        token_symbol = tx.get("tokenSymbol")
        from_addr = tx.get("from")
        to_addr = tx.get("to")
        value = int(tx.get("value", "0"))
        time_stamp = int(tx.get("timeStamp", "0"))

        if value > 0:
            trade = {
                "hash": tx_hash,
                "token": token_symbol,
                "from": from_addr,
                "to": to_addr,
                "value": value,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time_stamp)),
            }
            new_trades.append(trade)
            processed_txs.add(tx_hash)
    return new_trades

def simulate_trade_execution(trades):
    for trade in trades:
        print(f"Simulation: Trade {trade['hash']} token {trade['token']} from {trade['from']} to {trade['to']} value {trade['value']}")

def load_wallets_to_follow(filepath="src/v2/advanced/copy_trading/wallets_to_follow.json"):
    if not os.path.exists(filepath):
        print(f"⚠️ Fichier wallets_to_follow introuvable : {filepath}")
        return []
    with open(filepath, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    wallets = load_wallets_to_follow()
    if not wallets:
        print("Aucun wallet à suivre.")
    for wallet in wallets:
        print(f"Suivi des transactions du wallet : {wallet}")
        txs = get_wallet_transactions(wallet)
        new_trades = process_transactions(txs)
        if new_trades:
            simulate_trade_execution(new_trades)
        else:
            print(f"Aucune nouvelle transaction pour {wallet}.")