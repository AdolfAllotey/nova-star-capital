# -*- coding: utf-8 -*-
"""
Strategy API (v2) — endpoints:
- GET /api/strategy/_status
- GET /api/strategy/_diag
- GET /api/strategy/top
- GET /api/strategy/allocations
Compatibles avec les tests que tu lances via curl.
"""

from typing import Dict, List, Tuple
import os
import math
import time
from fastapi import APIRouter, HTTPException, Query
import httpx

# --------------------------- Constantes ---------------------------
TAG = "strategy-v2"
CACHE_TTL_S = 60

# --------------------------- Résolution URL OHLCV ---------------------------
def _resolve_ohlcv_url() -> str:
    """
    Ordre de résolution :
      1) NSC_STRATEGY_OHLCV_URL
      2) NSC_OHLCV_BASE_URL
      3) fallback local (même service)
    """
    return (
        os.getenv("NSC_STRATEGY_OHLCV_URL")
        or os.getenv("NSC_OHLCV_BASE_URL")
        or "http://127.0.0.1:8000/api/ohlcv/ohlcv"
    )

OHLCV_URL = _resolve_ohlcv_url()

# --------------------------- Router ---------------------------
router = APIRouter(prefix="/api/strategy", tags=["strategy"])

# --------------------------- Helpers ---------------------------
def _now_ms() -> float:
    return round((time.time_ns() / 1e6), 1)

async def _fetch_ohlcv(symbol: str, tf: str, limit: int) -> List[dict]:
    """
    Appelle l’endpoint OHLCV attendu: GET OHLCV_URL?symbol=...&tf=...&limit=...
    Retour: liste JSON [{...}, ...]
    """
    url = _resolve_ohlcv_url()
    params = {"symbol": symbol, "tf": tf, "limit": str(limit)}
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"OHLCV HTTP {r.status_code}: {r.text[:200]}")
        try:
            data = r.json()
            if not isinstance(data, list):
                raise ValueError("payload non-list")
            return data
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"OHLCV payload invalide: {e!r}")

def _mock_score_for(i: int) -> float:
    # Renvoie 60, 58, 56... (comme dans tes tests)
    return max(0.0, 60.0 - 2.0 * i)

def _score_from_ohlcv(rows: List[dict]) -> float:
    """
    Score très simple et stable: si on a des données -> 50 + log(len)
    (pas d’enjeu métier ici, juste pour débloquer le run)
    """
    if not rows:
        return 0.0
    return round(50.0 + math.log(len(rows) + 1), 1)

def _parse_symbols_param(symbols_param: str) -> List[str]:
    # Accepte "BTCUSDT,ETHUSDT" ou "BTCUSDT" etc.
    parts = [p.strip() for p in symbols_param.split(",") if p.strip()]
    uniq = []
    for s in parts:
        if s not in uniq:
            uniq.append(s)
    return uniq

# --------------------------- Endpoints ---------------------------
@router.get("/_status")
def _status():
    return {"ok": True, "tag": TAG}

@router.get("/_diag")
def _diag():
    return {
        "ok": True,
        "tag": TAG,
        "cache_ttl_s": CACHE_TTL_S,
        "ohlcv_url": _resolve_ohlcv_url(),
        "env": {
            "NSC_STRATEGY_OHLCV_URL": os.getenv("NSC_STRATEGY_OHLCV_URL", ""),
            "NSC_OHLCV_BASE_URL": os.getenv("NSC_OHLCV_BASE_URL", ""),
        },
    }

@router.get("/top")
async def top(
    symbols: str = Query(..., description="Liste CSV: e.g. BTCUSDT,ETHUSDT,SOLUSDT"),
    tf: str = "1h",
    lookback: int = 96,
    n: int = 3,
    mock: int = 0,
    details: int = 0,
):
    """
    /top?symbols=BTCUSDT,ETHUSDT,SOLUSDT&tf=1h&lookback=96&n=3&mock=0&details=1
    """
    t0 = _now_ms()
    syms = _parse_symbols_param(symbols)
    per_symbol_details: Dict[str, dict] = {}
    picks: List[Tuple[str, float]] = []

    # Mock path (utilisé par tes tests de validation)
    if mock:
        for i, s in enumerate(syms):
            sc = _mock_score_for(i)
            picks.append((s, sc))
            if details:
                per_symbol_details[s] = {"score": sc}
        picks.sort(key=lambda x: x[1], reverse=True)
        return {
            "tf": tf,
            "lookback": lookback,
            "n": n,
            "picks": [{"symbol": s, "score": sc} for s, sc in picks[:n]],
            "details": per_symbol_details if details else None,
            "_ms": round(_now_ms() - t0, 1),
        }

    # Réel
    url = _resolve_ohlcv_url()
    if not url:
        # Cas de garde: devrait être résolu par le fallback
        for s in syms:
            if details:
                per_symbol_details[s] = {"error": "OHLCV_URL non défini (résolution échouée)", "score": 0.0}
            picks.append((s, 0.0))
    else:
        for s in syms:
            try:
                rows = await _fetch_ohlcv(s, tf=tf, limit=lookback)
                sc = _score_from_ohlcv(rows)
                picks.append((s, sc))
                if details:
                    per_symbol_details[s] = {"score": sc, "samples": len(rows)}
            except HTTPException as e:
                # Message d’erreur explicite
                msg = e.detail if isinstance(e.detail, str) else str(e.detail)
                if details:
                    per_symbol_details[s] = {"error": f"{getattr(e, 'status_code', 502)}: {msg}", "score": 0.0}
                picks.append((s, 0.0))

    picks.sort(key=lambda x: x[1], reverse=True)
    out = {
        "tf": tf,
        "lookback": lookback,
        "n": n,
        "picks": [{"symbol": s, "score": sc} for s, sc in picks[:n]],
        "_ms": round(_now_ms() - t0, 1),
    }
    if details:
        out["details"] = per_symbol_details
    return out

@router.get("/allocations")
def allocations(
    symbols: List[str] = Query(..., description="Peut être répété: &symbols=BTCUSDT&symbols=ETHUSDT ..."),
    budget: float = 0.0,
    tf: str = "1h",
    lookback: int = 96,
    mock: int = 0,
):
    """
    /allocations?symbols=BTCUSDT&symbols=ETHUSDT&symbols=SOLUSDT&budget=5000&tf=1h&lookback=96&mock=0
    Allocation égale simple (place-holder).
    """
    if not symbols:
        return {"allocations": []}
    k = len(symbols)
    if k <= 0 or budget <= 0:
        return {"allocations": []}
    part = round(budget / k, 2)
    return {
        "tf": tf,
        "lookback": lookback,
        "budget": float(budget),
        "allocations": [{"symbol": s, "amount": part} for s in symbols],
        "_ms": 0.0,
    }
