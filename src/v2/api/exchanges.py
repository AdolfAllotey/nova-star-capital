# src/v2/api/exchanges.py
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["exchanges"])

SUPPORTED_EXCHANGES = ["binance"]   # on pourra y ajouter "mexc"
DEFAULT_EXCHANGE = "binance"

@router.get("/exchanges", summary="List supported exchanges and defaults")
def list_exchanges():
    return {
        "supported": SUPPORTED_EXCHANGES,
        "default": DEFAULT_EXCHANGE,
    }
