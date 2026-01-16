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
# NSC_PATCH: transfer_to_subaccount BEGIN
def transfer_to_subaccount(to_email: str, asset: str, amount: float):
    """
    Transfert vers sous-compte (Binance Sub-Account API).
    Endpoint: /sapi/v1/sub-account/transfer/subToSub
    NOTE: nécessite permissions Sub-Account sur ta clé API.
    """
    if not to_email:
        raise ValueError("to_email is required")
    if not asset:
        raise ValueError("asset is required")
    if amount is None or float(amount) <= 0:
        raise ValueError("amount must be > 0")

    endpoint = "/sapi/v1/sub-account/transfer/subToSub"
    payload = f"toEmail={to_email}&asset={asset}&amount={amount}"
    return _send_signed_request("POST", endpoint, payload)
# NSC_PATCH: transfer_to_subaccount END


# NSC_PATCH: binance_api_public_price BEGIN
def _norm_symbol(symbol: str) -> str:
    """
    Normalise un symbole pour Binance spot ticker.
    Ex: 'BTCUSDT' -> 'BTCUSDT', 'btc/usdt' -> 'BTCUSDT', 'BTC-USDT' -> 'BTCUSDT'
    """
    if not symbol:
        return ""
    sym = str(symbol).upper().strip()
    sym = sym.replace("/", "").replace("-", "").replace("_", "")
    return sym

def get_price(symbol: str):
    """
    Prix spot Binance via endpoint PUBLIC /api/v3/ticker/price (pas de signature).
    Retourne float ou None (fail-safe).
    """
    try:
        sym = _norm_symbol(symbol)
        if not sym:
            return None
        url = f"{BASE_URL}/api/v3/ticker/price"
        r = requests.get(url, params={"symbol": sym}, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        px = data.get("price")
        if px is None:
            return None
        return float(px)
    except Exception:
        return None

def token_available(symbol: str) -> bool:
    """
    True si le symbole est disponible côté Binance (au sens "ticker/price répond").
    Fail-safe => False.
    """
    try:
        return get_price(symbol) is not None
    except Exception:
        return False
# NSC_PATCH: binance_api_public_price END

