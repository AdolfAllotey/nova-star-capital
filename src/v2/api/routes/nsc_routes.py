# -*- coding: utf-8 -*-
# src/v2/api/routes/nsc_routes.py

from __future__ import annotations

import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

# --- Dossiers & fichiers de données (adapte si besoin) ---
BASE = Path("/opt/nsc")  # racine projet serveur (à ajuster selon ton arbo)
DATA = BASE / "src" / "v2" / "data"

REPORTS_DIR = DATA / "reports"
RISK_DIR = DATA / "risk"
PORTFOLIO_DIR = DATA / "portfolio"
SIGNALS_DIR = DATA / "signals"
SYSTEM_DIR = DATA / "system"

# Fichiers usuels
TRADE_SIM_FILE = REPORTS_DIR / "trade_simulation.json"
OPEN_POS_FILE = PORTFOLIO_DIR / "open_positions.json"
PNL_SERIES_FILE = REPORTS_DIR / "pnl_series.json"
MARKET_REGIME_FILE = REPORTS_DIR / "market_regime.json"
SENTIMENT_FILE = REPORTS_DIR / "average_sentiment.json"
MOMENTUM_FILE = REPORTS_DIR / "average_momentum.json"  # si séparé
SYSTEM_INFO_FILE = SYSTEM_DIR / "system_info.json"

WORST_TRADES_FILE = RISK_DIR / "worst_trades.json"
WORST_TRADES_SUMMARY_FILE = RISK_DIR / "worst_trades_summary.json"

WHALES_FILE = SIGNALS_DIR / "whales.json"  # ou signals/whales.json


# --- Utils --------------------------------------------------------------------

def iso_now() -> str:
    # ISO8601 UTC pour éviter "string did not match expected pattern" côté front
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists() and path.stat().st_size > 0:
            import json
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def ensure_number(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def coerce_iso8601(s: Optional[str]) -> str:
    """Retourne une date ISO8601Z. Si invalide/absente -> maintenant."""
    if not s:
        return iso_now()
    try:
        # tente parse + reformat
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return iso_now()


# ------------------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------------------

@router.get("/dashboard/market_regime")
def dashboard_market_regime():
    """
    Retour format:
    {
      "regime": "BULL" | "BEAR" | "NEUTRAL",
      "score": 0.72,
      "date": "2025-10-31T12:55:00Z"
    }
    """
    d = load_json(MARKET_REGIME_FILE, {})
    regime = (d.get("regime") or d.get("label") or "—").upper()
    score = ensure_number(d.get("score"))
    date = coerce_iso8601(d.get("date"))
    return {"regime": regime, "score": score, "date": date}


@router.get("/dashboard/sentiment_momentum")
def dashboard_sentiment_momentum():
    """
    Retour:
    {
      "sentiment": 0.61,
      "momentum": 0.58,
      "date": "2025-10-31T12:55:00Z"
    }
    """
    s = load_json(SENTIMENT_FILE, {})
    m = load_json(MOMENTUM_FILE, {})
    # fichiers parfois liste -> gère les 2 cas
    if isinstance(s, list) and s:
        s = s[-1]
    if isinstance(m, list) and m:
        m = m[-1]
    sentiment = ensure_number((s or {}).get("value", (s or {}).get("score", 0)))
    momentum = ensure_number((m or {}).get("value", (m or {}).get("score", 0)))
    date = coerce_iso8601((s or {}).get("date") or (m or {}).get("date"))
    return {"sentiment": sentiment, "momentum": momentum, "date": date}


@router.get("/system/info")
def system_info():
    """
    Pour le widget "System Metrics" du Dashboard.
    """
    d = load_json(SYSTEM_INFO_FILE, {})
    app = d.get("app") or "nsc-api"
    py = d.get("python") or d.get("py") or ""
    host = d.get("host") or socket.gethostname()
    return {"app": app, "py": py, "host": host}


@router.get("/pnl/recent")
def pnl_recent():
    """
    Série pour le graphe PnL. Le front accepte un tableau [{x, y}] ou [{label, value}].
    On renvoie dans les deux champs pour compatibilité.
    """
    series = load_json(PNL_SERIES_FILE, [])

    def _coerce_point(p: Dict[str, Any]) -> Dict[str, Any]:
        label = p.get("label") or p.get("x") or ""
        y = p.get("y", p.get("value", 0))
        # si label ressemble à une date -> normalise
        try:
            label_iso = coerce_iso8601(label)
            label_short = label  # laisse l'étiquette originale si déjà “M-1”, etc.
        except Exception:
            label_iso = iso_now()
            label_short = str(label)
        return {"x": label_short, "y": ensure_number(y), "label": label_short, "value": ensure_number(y), "date": label_iso}

    if not isinstance(series, list):
        series = []

    coerced = [_coerce_point(p if isinstance(p, dict) else {}) for p in series]
    if not coerced:
        coerced = [
            {"x": "M-2", "y": 1000, "label": "M-2", "value": 1000, "date": iso_now()},
            {"x": "M-1", "y": -300, "label": "M-1", "value": -300, "date": iso_now()},
            {"x": "M", "y": 500, "label": "M", "value": 500, "date": iso_now()},
        ]
    return {"series": coerced, "unit": "€"}
# ------------------------------------------------------------------------------
# TRADES
# ------------------------------------------------------------------------------

@router.get("/trades/open")
def trades_open():
    """
    Attend un fichier trade_simulation.json avec des objets { ... , "status": "open" }.
    """
    trades = load_json(TRADE_SIM_FILE, [])
    if not isinstance(trades, list):
        trades = []
    open_trades = [t for t in trades if (str(t.get("status") or "").lower() in ("open", "ongoing", "running"))]
    return {"trades": open_trades}


@router.get("/trades/history")
def trades_history():
    trades = load_json(TRADE_SIM_FILE, [])
    if not isinstance(trades, list):
        trades = []
    closed = [t for t in trades if (str(t.get("status") or "").lower() in ("closed", "done", "exit", "exited"))]
    return {"trades": closed}


# ------------------------------------------------------------------------------
# POSITIONS
# ------------------------------------------------------------------------------

@router.get("/portfolio/open")
def portfolio_open():
    """
    open_positions.json → liste d'objets positions.
    """
    positions = load_json(OPEN_POS_FILE, [])
    if not isinstance(positions, list):
        positions = []
    return {"positions": positions}


# ------------------------------------------------------------------------------
# WHALES / SIGNALS
# ------------------------------------------------------------------------------

@router.get("/signals/whales")
def signals_whales():
    """
    whales.json  → [{...}]
    """
    events = load_json(WHALES_FILE, [])
    if not isinstance(events, list):
        events = []
    return {"events": events}


# ------------------------------------------------------------------------------
# RISK / WORST TRADES
# ------------------------------------------------------------------------------

@router.get("/risk/worst")
def risk_worst():
    """
    worst_trades.json -> { "trades": [...] } OU [ ... ]
    """
    w = load_json(WORST_TRADES_FILE, [])
    if isinstance(w, dict):
        trades = w.get("trades", [])
    else:
        trades = w if isinstance(w, list) else []
    return {"trades": trades}


@router.get("/risk/worst/summary")
def risk_worst_summary():
    """
    worst_trades_summary.json -> string OU { "summary": "...", ... }
    """
    s = load_json(WORST_TRADES_SUMMARY_FILE, "")
    if isinstance(s, dict):
        summary = s.get("summary") or s.get("text") or ""
    else:
        summary = str(s)
    return {"summary": summary or "—"}
