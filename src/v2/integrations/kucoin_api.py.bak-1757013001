# src/v2/integrations/kucoin_api.py

import os
import time
import base64
import hashlib
import hmac
import requests

KUCOIN_API_KEY = os.getenv("KUCOIN_API_KEY")
KUCOIN_API_SECRET = os.getenv("KUCOIN_API_SECRET")
KUCOIN_API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")
KUCOIN_BASE_URL = "https://api.kucoin.com"

def _get_timestamp():
    return str(int(time.time() * 1000))

def _sign_request(method, endpoint, body=""):
    now = _get_timestamp()
    str_to_sign = now + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(KUCOIN_API_SECRET.encode(), str_to_sign.encode(), hashlib.sha256).digest()
    ).decode()
    passphrase = base64.b64encode(
        hmac.new(KUCOIN_API_SECRET.encode(), KUCOIN_API_PASSPHRASE.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "KC-API-KEY": KUCOIN_API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": now,
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }
    return headers

def get_account_balances():
    endpoint = "/api/v1/accounts"
    headers = _sign_request("GET", endpoint)
    response = requests.get(KUCOIN_BASE_URL + endpoint, headers=headers)
    return response.json()

def get_balance_for_asset(asset="USDT"):
    balances = get_account_balances()
    if "data" not in balances:
        return None
    for entry in balances["data"]:
        if entry["currency"] == asset and entry["type"] == "trade":
            return float(entry["available"]), float(entry["holds"])
    return None

if __name__ == "__main__":
    print(get_account_balances())