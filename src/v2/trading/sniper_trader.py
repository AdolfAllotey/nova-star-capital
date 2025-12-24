import os
import time
import json
import requests
from datetime import datetime, timezone, timezone
from src.utils.telegram_bot import send_telegram_message

# === PARAMÈTRES ===
MIN_MARKETCAP = 35000
MAX_DOMINANT_WALLET = 5.0  # %
MIN_SCORE = 65
MIN_SENTIMENT = 0.2
SIMULATION_MODE = True

# === DÉTECTION MOCK / À REMPLACER PAR API DEX Screener ou GeckoTerminal ===
def fetch_new_tokens():
    """
    Exemple de tokens détectés récemment (mock).
    À remplacer par intégration API réelle (DEX Screener, GeckoTerminal, GMGN.ai...).
    """
    try:
        with open("data/samples/sniper_tokens_sample.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Fichier de détection non trouvé.")
        return []

# === FILTRAGE ===
def is_valid_candidate(token):
    return (
        token.get("marketcap", 0) >= MIN_MARKETCAP and
        token.get("dominant_wallet", 100) <= MAX_DOMINANT_WALLET and
        token.get("score", 0) >= MIN_SCORE and
        token.get("sentiment", 0) >= MIN_SENTIMENT and
        not token.get("blacklisted", False)
    )

# === ACTION (simulation ou réel) ===
def execute_trade(token):
    name = token.get("name")
    symbol = token.get("symbol")
    price = token.get("price")
    tg_msg = (
        f"🎯 *Sniper Alert*\n\n"
        f"Token: `{symbol}` ({name})\n"
        f"Score: {token.get('score')} | Sentiment: {token.get('sentiment')}\n"
        f"Marketcap: ${token.get('marketcap'):,} | Dominant wallet: {token.get('dominant_wallet')}%\n"
        f"💰 Prix d'entrée: ${price}\n"
        f"{'🧪 Simulation activée' if SIMULATION_MODE else '🟢 Achat réel déclenché'}"
    )
    send_telegram_message(tg_msg, parse_mode="Markdown")

    # Simuler ou exécuter un achat
    if SIMULATION_MODE:
        print(f"✅ Simulation d’achat pour {symbol}")
    else:
        # TODO: ajouter intégration réelle DEX / wallet
        print(f"🟢 Achat réel lancé pour {symbol}")

# === PIPELINE ===
def main():
    print("🚀 Lancement du sniper trader...\n")
    tokens = fetch_new_tokens()
    print(f"🔍 {len(tokens)} token(s) détectés.")
    for token in tokens:
        if is_valid_candidate(token):
            execute_trade(token)
            time.sleep(1)  # anti-rate limit

if __name__ == "__main__":
    main()