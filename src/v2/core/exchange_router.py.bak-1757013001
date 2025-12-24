# src/v2/core/exchange_router.py

import json
import os

EXCHANGE_MAP_PATH = "src/v2/data/config/token_exchange_map.json"

def load_exchange_map():
    """Charge le mapping token → plateforme depuis le fichier JSON."""
    if not os.path.exists(EXCHANGE_MAP_PATH):
        raise FileNotFoundError(f"Fichier {EXCHANGE_MAP_PATH} introuvable.")
    
    with open(EXCHANGE_MAP_PATH, "r") as f:
        return json.load(f)

def get_exchange_for_token(token_symbol):
    """
    Retourne la plateforme associée à un token donné.
    Par défaut 'binance' si le token n'est pas dans le mapping.
    """
    try:
        exchange_map = load_exchange_map()
        return exchange_map.get(token_symbol.upper(), "binance")
    except Exception as e:
        print(f"[Exchange Router] Erreur : {e}")
        return "binance"