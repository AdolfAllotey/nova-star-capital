# /opt/nsc/app/src/v2/api/routers/ohlcv.py
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query, HTTPException
from typing import Literal, List, Dict
import random
import csv
import io

router = APIRouter(tags=["internal"])

# Générateur mock simple de bougies; à remplacer par une vraie source (ccxt, binance, db…)
def generate_ohlcv(symbol: str, tf: Literal["1m","5m","15m","1h","4h","1d"], days: int) -> List[Dict]:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    step = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
    }[tf]
    n = max(10, int((timedelta(days=days) / step)))  # au moins 10 points

    price = 50000.0
    out = []
    t = now - step * n
    for _ in range(n):
        # mini random walk
        drift = random.uniform(-50, 50)
        o = price
        h = o + abs(drift) * random.uniform(0.5, 1.2)
        l = o - abs(drift) * random.uniform(0.5, 1.2)
        c = max(l, min(h, o + drift))
        v = random.uniform(5, 50)
        out.append({
            "ts": int(t.timestamp()*1000),
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": round(v, 3),
            "symbol": symbol,
            "tf": tf,
        })
        price = c
        t += step
    return out

@router.get("/internal/ohlcv")
def internal_ohlcv(
    symbol: str = Query(..., description="ex: BTCUSDT"),
    tf: Literal["1m","5m","15m","1h","4h","1d"] = Query("1h"),
    days: int = Query(30, ge=1, le=365),
    format: Literal["json","csv"] = Query("json"),
):
    data = generate_ohlcv(symbol, tf, days)

    if format == "json":
        return {"symbol": symbol, "tf": tf, "count": len(data), "data": data}

    # CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ts","open","high","low","close","volume","symbol","tf"])
    for r in data:
        writer.writerow([r["ts"], r["open"], r["high"], r["low"], r["close"], r["volume"], r["symbol"], r["tf"]])
    return buf.getvalue()
