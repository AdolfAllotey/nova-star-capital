import os
from dotenv import load_dotenv
from web3 import Web3

# Charger les variables d'environnement depuis src/v2/.env
load_dotenv(dotenv_path="src/v2/.env")

INFURA_PROJECT_ID = os.getenv("INFURA_PROJECT_ID")
if not INFURA_PROJECT_ID:
    raise ValueError("❌ Variable INFURA_PROJECT_ID non définie dans src/v2/.env")

INFURA_URL = f"https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}"

w3 = Web3(Web3.HTTPProvider(INFURA_URL))

def detect_new_tokens(block_start, block_end):
    transfer_event_signature = w3.keccak(text="Transfer(address,address,uint256)").hex()
    print(f"Écoute des blocks {block_start} à {block_end}...")

    for block_num in range(block_start, block_end + 1):
        print(f"Block {block_num}")
        block = w3.eth.getBlock(block_num, full_transactions=True)
        for tx in block.transactions:
            receipt = w3.eth.getTransactionReceipt(tx.hash)
            for log in receipt.logs:
                if log.topics[0].hex() == transfer_event_signature:
                    from_address = "0x" + log.topics[1].hex()[-40:]
                    if from_address == "0x0000000000000000000000000000000000000000":
                        token_address = log.address
                        print(f"Nouveau token détecté : {token_address} au block {block_num}")

if __name__ == "__main__":
    latest_block = w3.eth.block_number
    detect_new_tokens(latest_block - 10, latest_block)