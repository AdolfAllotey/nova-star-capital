from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="src/v2/.env")

INFURA_PROJECT_ID = os.getenv("INFURA_PROJECT_ID")
if not INFURA_PROJECT_ID:
    raise ValueError("❌ INFURA_PROJECT_ID non défini dans src/v2/.env")

WS_PROVIDER = f"wss://mainnet.infura.io/ws/v3/{INFURA_PROJECT_ID}"

w3 = Web3(Web3.WebsocketProvider(WS_PROVIDER))

def handle_pending_tx(tx_hash):
    print(f"Tx en mempool reçue : {tx_hash}")

def main():
    print("Connexion au provider WebSocket...")
    subscription = w3.eth.subscribe('pendingTransactions', handle_pending_tx)
    print("Abonnement activé, réception des transactions en attente...")

if __name__ == "__main__":
    main()