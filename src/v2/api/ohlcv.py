from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from typing import Optional
from datetime import datetime, timedelta
import random
import io
import csv

# Router sans prefix : le prefix "/api/ohlcv" est géré dans server.py
router = APIRouter()

@router.get("/ohlcv", response_model=None)
async def get_ohlcv(
    symbol: str,
    tf: str = Query(..., description="Timeframe, ex: 1h"),
    limit: Optional[int] = Query(100, description="Nombre de bougies"),
    days: Optional[int] = Query(None, description="Nombre de jours à générer"),
    format: str = Query("json", description="json ou csv"),
):
    """Endpoint OHLCV mock pour tests"""
    now = datetime.utcnow()
    data = []
    n = limit or (24 * (days or 1))
    for i in range(n):
        ts = now - timedelta(minutes=i * 60)
        o = random.uniform(100, 200)
        h = o + random.uniform(0, 5)
        l = o - random.uniform(0, 5)
        c = random.uniform(l, h)
        v = random.randint(1000, 5000)
        data.append(
            {
                "symbol": symbol,
                "tf": tf,
                "ts": ts.isoformat(),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
            }
        )
    data.reverse()

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return Response(content=output.getvalue(), media_type="text/csv")

    return data
