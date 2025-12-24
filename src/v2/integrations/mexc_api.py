import requests
import hmac
import hashlib
import time
import os

MEXC_API_KEY = os.getenv("MEXC_API_KEY")
MEXC_SECRET_KEY = os.getenv("MEXC_SECRET_KEY")
BASE_URL = os.getenv("MEXC_BASE_URL", "https://api.mexc.com")

def _get_timestamp():
    return str(int(time.time() * 1000))

def _sign(params):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(MEXC_SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def _headers():
    return {
        "Content-Type": "application/json",
        "ApiKey": MEXC_API_KEY
    }

def get_price(symbol):
    try:
        response = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol.upper()})
        response.raise_for_status()
        return float(response.json()["price"])
    except Exception as e:
        print(f"Erreur get_price MEXC : {e}")
        return None

def get_balance(token):
    try:
        url = f"{BASE_URL}/api/v3/account"
        timestamp = _get_timestamp()
        params = {"timestamp": timestamp}
        params["signature"] = _sign(params)
        response = requests.get(url, headers=_headers(), params=params)
        response.raise_for_status()
        balances = response.json().get("balances", [])
        for asset in balances:
            if asset["asset"].upper() == token.upper():
                return float(asset["free"])
        return 0.0
    except Exception as e:
        print(f"Erreur get_balance MEXC : {e}")
        return None

def place_order(symbol, amount, side="BUY", order_type="MARKET"):
    try:
        url = f"{BASE_URL}/api/v3/order"
        timestamp = _get_timestamp()
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": amount,
            "timestamp": timestamp
        }
        params["signature"] = _sign(params)
        response = requests.post(url, headers=_headers(), params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erreur place_order MEXC : {e}")
        return None

def get_open_orders(symbol):
    try:
        url = f"{BASE_URL}/api/v3/openOrders"
        timestamp = _get_timestamp()
        params = {
            "symbol": symbol.upper(),
            "timestamp": timestamp
        }
        params["signature"] = _sign(params)
        response = requests.get(url, headers=_headers(), params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erreur get_open_orders MEXC : {e}")
        return []

def cancel_order(symbol, order_id):
    try:
        url = f"{BASE_URL}/api/v3/order"
        timestamp = _get_timestamp()
        params = {
            "symbol": symbol.upper(),
            "orderId": order_id,
            "timestamp": timestamp
        }
        params["signature"] = _sign(params)
        response = requests.delete(url, headers=_headers(), params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erreur cancel_order MEXC : {e}")
        return None