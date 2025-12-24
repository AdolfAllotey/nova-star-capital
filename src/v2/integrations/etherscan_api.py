import requests
import os
from datetime import datetime, timezone, timezone, timedelta
from src.v2.utils.logger import get_logger

logger = get_logger("etherscan_api")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETHERSCAN_BASE_URL = "https://api.etherscan.io/api/v2"

# Optionnel : support d'autres chainId si multichain prévu
DEFAULT_CHAIN_ID = 1  # Ethereum Mainnet

def get_transactions_for_address(address, chain_id=DEFAULT_CHAIN_ID, start_block=0, end_block=99999999, page=1, offset=100):
    url = f"{ETHERSCAN_BASE_URL}/accounts/{address}/transactions"
    params = {
        "chainId": chain_id,
        "startblock": start_block,
        "endblock": end_block,
        "page": page,
        "offset": offset,
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "1":
            return data.get("result", [])
        else:
            logger.warning(f"Aucune transaction trouvée ou erreur API : {data.get('message')}")
            return []
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transactions Etherscan : {e}")
        return []

def get_internal_transactions(address, chain_id=DEFAULT_CHAIN_ID):
    url = f"{ETHERSCAN_BASE_URL}/accounts/{address}/transactions/internal"
    params = {
        "chainId": chain_id,
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "1":
            return data.get("result", [])
        else:
            logger.warning(f"Aucune transaction interne trouvée : {data.get('message')}")
            return []
    except Exception as e:
        logger.error(f"Erreur récupération tx internes : {e}")
        return []

def get_token_transfers(address, chain_id=DEFAULT_CHAIN_ID):
    url = f"{ETHERSCAN_BASE_URL}/accounts/{address}/tokentransfers"
    params = {
        "chainId": chain_id,
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "1":
            return data.get("result", [])
        else:
            logger.warning(f"Aucun transfert de token trouvé : {data.get('message')}")
            return []
    except Exception as e:
        logger.error(f"Erreur récupération token transfers : {e}")
        return []

# Exemple d'usage
if __name__ == "__main__":
    test_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"  # Exemple : wallet de Bitfinex
    txs = get_transactions_for_address(test_address)
    print(f"{len(txs)} transactions trouvées.")