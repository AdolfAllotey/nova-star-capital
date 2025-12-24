# src/v2/integrations/binance_api.py

import os
import requests
import hmac
import hashlib
import time

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
BASE_URL = "https://api.binance.com"

def _get_timestamp():
    return int(time.time() * 1000)

def _sign_payload(payload, secret):
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def _send_signed_request(http_method, endpoint, payload=""):
    timestamp = _get_timestamp()
    query_string = f"{payload}&timestamp={timestamp}" if payload else f"timestamp={timestamp}"
    signature = _sign_payload(query_string, BINANCE_API_SECRET)
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    response = requests.request(http_method, url, headers=headers)
    return response.json()

def get_account_balances():
    endpoint = "/api/v3/account"
    return _send_signed_request("GET", endpoint)

def get_balance_for_asset(asset="USDT"):
    account_info = get_account_balances()
    if "balances" not in account_info:
        return None
    for asset_info in account_info["balances"]:
        if asset_info["asset"] == asset:
            return float(asset_info["free"]), float(asset_info["locked"])
    return None

# Exemple d'appel futur : transfert vers sous-compte (nécessite API Sub-Account)
# def transfer_to_subaccount(email, asset, amount):
#     endpoint = "/sapi/v1/sub-account/transfer/subToSub"
#     payload = f"toEmail={email}&asset={asset}&amount={amount}"
#     return _send_signed_request("POST", endpoint, payload)

if __name__ == "__main__":
    print(get_account_balances())