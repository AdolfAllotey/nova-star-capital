from __future__ import annotations

import os
import math
from typing import Dict, List
import httpx

API_BASE = os.getenv("NSC_API_BASE", "http://127.0.0.1:8000")
_TIMESCALE_OK = {"1m", "5m", "15m", "1h", "4h", "1d"}

def _fetch_ohlcv(symbol: str, tf: str, limit: int) -> List[dict]:
    if tf not in _TIMESCALE_OK:
        raise ValueError(f"tf invalide: {tf} (attendu: {_TIMESCALE_OK})")
    url = f"{API_BASE}/api/ohlcv"
    params = {"symbol": symbol, "tf": tf, "limit": limit}
    with httpx.Client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or not data:
            raise RuntimeError(f"Réponse OHLCV vide pour {symbol} {tf}")
        return data

def _safe_pct(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return (a - b) / b

def _series(closes: List[float]) -> Dict[str, float]:
    n = len(closes)
    if n < 3:
        return {"ret_lb": 0.0, "slope": 0.0, "vol": 0.0}

    ret_lb = _safe_pct(closes[-1], closes[0])

    x_bar = (n - 1) / 2
    y_bar = sum(closes) / n
    num = sum((i - x_bar) * (closes[i] - y_bar) for i in range(n))
    den = sum((i - x_bar) ** 2 for i in range(n)) or 1.0
    slope = num / den
    if y_bar != 0:
        slope /= y_bar

    var = sum((c - y_bar) ** 2 for c in closes) / max(1, n - 1)
    vol = math.sqrt(var) / y_bar if y_bar else 0.0

    return {"ret_lb": ret_lb, "slope": slope, "vol": vol}

def _momentum_score_from_closes(closes: List[float]) -> float:
    s = _series(closes)
    return 0.7 * s["ret_lb"] + 0.3 * s["slope"] - 0.1 * s["vol"]

def score_universe(universe: List[str], tf: str = "1h", lookback: int = 96) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for sym in universe:
        try:
            ohlcv = _fetch_ohlcv(sym, tf=tf, limit=lookback)
            closes = [float(c["close"]) for c in ohlcv if "close" in c]
            if len(closes) < 3:
                scores[sym] = 0.0
                continue
            scores[sym] = _momentum_score_from_closes(closes)
        except Exception:
            scores[sym] = 0.0
    return scores
