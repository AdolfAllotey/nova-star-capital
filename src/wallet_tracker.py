from web3 import Web3
import json
from config.config_loader import load_config

def connect_to_rpc(chain: str):
    if chain == "eth":
        # Infura ou autre provider Ethereum
        return Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_INFURA_KEY"))
    elif chain == "bsc":
        # RPC public BSC
        return Web3(Web3.HTTPProvider("https://bsc-dataseed1.binance.org/"))
    else:
        raise ValueError("Chaîne non supportée")

def get_eth_balance(w3, address):
    balance_wei = w3.eth.get_balance(address)
    return w3.from_wei(balance_wei, 'ether')

def get_wallet_balances():
    config = load_config()
    balances = {}

    for chain in ["eth", "bsc"]:
        address = config["wallets"][chain]
        w3 = connect_to_rpc(chain)
        if not w3.is_connected():
            print(f"[❌] Impossible de se connecter à {chain}")
            continue
        balance = get_eth_balance(w3, address)
        balances[chain] = float(balance)
        print(f"[✅] {chain.upper()} Wallet: {balance:.4f} {chain.upper()}")

    return balances