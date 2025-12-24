from src.v2.integrations.binance_api import get_price as binance_get_price, place_order as binance_place_order, token_available as binance_has_token
from src.v2.integrations.mexc_api import get_price as mexc_get_price, place_order as mexc_place_order, token_available as mexc_has_token
from src.v2.utils.logger import get_logger

logger = get_logger("exchange_router")

def get_price(token_symbol):
    """Retourne le prix du token via la plateforme disponible."""
    if binance_has_token(token_symbol):
        logger.info(f"Routage vers Binance pour {token_symbol}")
        return binance_get_price(token_symbol)
    elif mexc_has_token(token_symbol):
        logger.info(f"Routage vers MEXC pour {token_symbol}")
        return mexc_get_price(token_symbol)
    else:
        logger.warning(f"Token {token_symbol} introuvable sur Binance ou MEXC.")
        return None

def place_order(token_symbol, amount, side="buy"):
    """Place un ordre d'achat ou de vente sur la plateforme appropriée."""
    if binance_has_token(token_symbol):
        logger.info(f"Placement ordre sur Binance - {side.upper()} {amount} {token_symbol}")
        return binance_place_order(token_symbol, amount, side)
    elif mexc_has_token(token_symbol):
        logger.info(f"Placement ordre sur MEXC - {side.upper()} {amount} {token_symbol}")
        return mexc_place_order(token_symbol, amount, side)
    else:
        logger.error(f"Impossible de placer l'ordre : {token_symbol} introuvable.")
        return {"error": "Token not available"}
