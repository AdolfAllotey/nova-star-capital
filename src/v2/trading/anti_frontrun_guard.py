import os
import time
from web3 import Web3
from datetime import datetime, timezone, timezone

# === Configuration RPC sécurisé (Flashbots Protect RPC)
FLASHBOTS_RPC = "https://rpc.flashbots.net"
w3 = Web3(Web3.HTTPProvider(FLASHBOTS_RPC))

def is_transaction_suspicious(tx):
    """
    Logique de base : détecter les transactions à risque (sandwich attack, gas war, etc.)
    À améliorer selon les besoins.
    """
    try:
        gas_price = int(tx.get("gasPrice", 0))
        max_priority_fee = int(tx.get("maxPriorityFeePerGas", 0))

        # Critère simple : gas price anormalement élevé
        if gas_price > Web3.to_wei(300, 'gwei'):
            return True
        if max_priority_fee > Web3.to_wei(5, 'gwei'):
            return True

        return False
    except Exception:
        return False

def scan_mempool(limit=20):
    """
    Récupère les dernières transactions depuis la mempool.
    (Note : Flashbots ne donne pas tout, mais protège les envois.)
    """
    print(f"🔍 Scan des transactions entrantes (limit={limit}) - {datetime.now().isoformat()}")

    try:
        pending_tx_hashes = w3.txpool.content()["pending"]
        suspicious = []

        for sender, txs in pending_tx_hashes.items():
            for nonce, tx in txs.items():
                if is_transaction_suspicious(tx):
                    suspicious.append({
                        "from": sender,
                        "hash": tx["hash"],
                        "gasPrice": tx.get("gasPrice"),
                        "maxPriorityFee": tx.get("maxPriorityFeePerGas")
                    })
                if len(suspicious) >= limit:
                    break
            if len(suspicious) >= limit:
                break

        if suspicious:
            print(f"🚨 Transactions suspectes détectées : {len(suspicious)}")
            for tx in suspicious:
                print(f"- From: {tx['from']} | Hash: {tx['hash']}")

        else:
            print("✅ Aucun frontrun suspect détecté.")

    except Exception as e:
        print(f"❌ Erreur lors de l’analyse de la mempool : {e}")

if __name__ == "__main__":
    scan_mempool()