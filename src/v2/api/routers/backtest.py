# /opt/nsc/app/src/v2/api/routers/backtest.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Literal
import httpx

from .security import require_basic_auth  # si tu as déjà un décorateur; sinon commente
from ...strategy.momentum import backtest_momentum

router = APIRouter(tags=["secure"])

@router.get("/api/secure/backtest")
# @require_basic_auth  # si besoin, sinon enlève
async def backtest(
    symbol: str = Query("BTCUSDT"),
    tf: Literal["1m","5m","15m","1h","4h","1d"] = Query("1h"),
    days: int = Query(60, ge=5, le=365),
    fast: int = Query(20, ge=2),
    slow: int = Query(50, ge=3),
):
    # Récupère les données via notre endpoint interne (même process)
    url = f"http://127.0.0.1:8000/internal/ohlcv?symbol={symbol}&tf={tf}&days={days}&format=json"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
    if r.status_code != 200:
        raise HTTPException(502, f"data source error ({r.status_code})")
    payload = r.json()
    ohlcv = payload.get("data", [])
    if len(ohlcv) < max(fast, slow) + 5:
        raise HTTPException(400, "Not enough data")

    res = backtest_momentum(ohlcv, fast=fast, slow=slow, fee_bp=5.0)
    return {
        "symbol": symbol,
        "tf": tf,
        "days": days,
        "fast": fast,
        "slow": slow,
        "metrics": res,
    }
