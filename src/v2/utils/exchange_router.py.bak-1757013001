# src/v2/utils/exchange_router.py

import json
import os

def load_token_exchange_map(filepath="src/v2/data/token_exchange_map.json"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"❌ Fichier introuvable : {filepath}")
    with open(filepath, "r") as f:
        return json.load(f)

def get_exchange_for_token(token: str, filepath="src/v2/data/token_exchange_map.json") -> str:
    """
    Retourne le nom de la plateforme pour un token donné ('binance', 'mexc', etc.)
    """
    token_exchange_map = load_token_exchange_map(filepath)
    return token_exchange_map.get(token.lower(), "binance")  # par défaut : binance