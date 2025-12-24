from __future__ import annotations

import csv
import io
import math
import os
from datetime import datetime, timezone
from typing import List, Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Response

router = APIRouter()

# Lecture de la base URL OHLCV moderne
def _get_modern_base_url() -> str:
    # priorité: NSC_STRATEGY_OHLCV_URL > NSC_OHLCV_BASE_URL > défaut local
    url = os.getenv(
        "NSC_STRATEGY_OHLCV_URL",
        os.getenv("NSC_OHLCV_BASE_URL", "http://127.0.0.1:8000/api/ohlcv/ohlcv"),
    )
    if not url:
        url = "http://127.0.0.1:8000/api/ohlcv/ohlcv"
    return url

@router.get("", summary="OHLCV (legacy JSON/CSV)")
def legacy_ohlcv(
    symbol: str = Query(..., description="Ex: BTCUSDT"),
    tf: Literal["1m","5m","15m","1h","4h","1d"] = Query("1h"),
    days: int = Query(2, ge=1, le=60, description="Fenêtre en jours"),
    format: Literal["json","csv"] = Query("json"),
) -> Response:
    """
    Endpoint legacy compatible :
    - JSON (liste d'objets) ou CSV (header: timestamp,open,high,low,close,volume,symbol,tf,exchange)
    - Convertit 'days' en 'limit' (= days*24 si tf=1h; formule générique sinon)
    """
    base = _get_modern_base_url()

    # Convertit days -> limit en fonction du timeframe (approx simple)
    tf_to_per_day = {"1m": 60*24, "5m": 12*24, "15m": 4*24, "1h": 24, "4h": 6, "1d": 1}
    per_day = tf_to_per_day.get(tf, 24)
    limit = max(1, min(1440, days * per_day))

    params = {"symbol": symbol, "tf": tf, "limit": str(limit)}

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(base, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"backend error: {resp.text[:200]}")
        data = resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fetch failed: {e!r}")

    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        # En-tête
        w.writerow(["timestamp","open","high","low","close","volume","symbol","tf","exchange"])
        for row in data:
            # le backend moderne renvoie déjà ces champs; on sécurise un minimum
            ts = row.get("timestamp") or row.get("ts")
            if isinstance(ts, (int, float)):
                ts_iso = datetime.fromtimestamp(ts/1000 if ts > 10_000_000_000 else ts, tz=timezone.utc).isoformat()
            else:
                ts_iso = str(ts)
            w.writerow([
                ts_iso,
                row.get("open"),
                row.get("high"),
                row.get("low"),
                row.get("close"),
                row.get("volume"),
                row.get("symbol", symbol),
                row.get("tf", tf),
                row.get("exchange", "unknown"),
            ])
        csv_body = buf.getvalue()
        return Response(
            content=csv_body,
            media_type="text/csv",
            headers={"Content-Disposition": f'inline; filename="{symbol}_{tf}_{days}d.csv"'},
        )

    # JSON
    return Response(content=httpx.Response(200, json=data).text, media_type="application/json")

@router.get("/__legacy_alive__", summary="Ping legacy", include_in_schema=False)
def legacy_alive() -> dict:
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@router.get("/__echo_env__", summary="Echo env", include_in_schema=False)
def echo_env() -> dict:
    return {
        "NSC_STRATEGY_OHLCV_URL": os.getenv("NSC_STRATEGY_OHLCV_URL"),
        "NSC_OHLCV_BASE_URL": os.getenv("NSC_OHLCV_BASE_URL"),
    }
