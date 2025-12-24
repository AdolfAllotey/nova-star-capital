import os
from src.utils.telegram_bot import send_telegram_message

# Mode trading : True pour réel, False pour simulation
REAL_TRADING = os.getenv("REAL_TRADING", "False").lower() == "true"

def execute_trade(order):
    """
    Execute un ordre d'achat ou de vente.

    order: dict avec au moins les clés :
        - symbol (str) : token à trader
        - side (str) : 'buy' ou 'sell'
        - quantity (float) : quantité à acheter/vendre
    """
    symbol = order.get("symbol")
    side = order.get("side")
    quantity = order.get("quantity")

    if REAL_TRADING:
        # TODO: implémenter appel API exchange ici
        # Exemple: binance_api.place_order(symbol, side, quantity)
        send_telegram_message(f"🚀 Ordre {side.upper()} exécuté pour {quantity} {symbol} (REEL)")
        print(f"[REEL] {side} {quantity} {symbol}")
    else:
        # Mode simulation : juste logging
        send_telegram_message(f"📝 Ordre {side.upper()} simulé pour {quantity} {symbol}")
        print(f"[SIMU] {side} {quantity} {symbol}")

if __name__ == "__main__":
    # Test simple
    test_order = {"symbol": "BTCUSDT", "side": "buy", "quantity": 0.001}
    execute_trade(test_order)