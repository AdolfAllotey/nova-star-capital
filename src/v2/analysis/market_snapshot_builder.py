from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.v2.utils.logger import get_logger

logger = get_logger("market_snapshot_builder")

DATA_DIR = os.getenv("DATA_DIR", "/opt/nsc/data/preprod")
OUT = Path(DATA_DIR) / "market_snapshot.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_default(status: str, reason: str) -> Dict[str, Any]:
    return {
        "ts": _utc_now(),
        "vix": 0.0,
        "qqq": {"close": 0.0, "ma50": 0.0, "ma200": 0.0, "ret_20d": 0.0},
        "spy": {"close": 0.0, "ma50": 0.0, "ma200": 0.0, "ret_20d": 0.0},
        "breadth": {"pct_above_ma200": None},
        "status": status,
        "reason": reason,
        "source": "yfinance",
    }


def _compute_metrics(df, label: str) -> Dict[str, float]:
    """Compute close/MA50/MA200/ret_20d robustly from yfinance output."""
    try:
        import pandas as pd  # type: ignore

        if df is None or len(df) == 0:
            return {"close": 0.0, "ma50": 0.0, "ma200": 0.0, "ret_20d": 0.0}

        # Get a "Close" SERIES (handles MultiIndex columns)
        if hasattr(df, "columns") and isinstance(getattr(df, "columns"), pd.MultiIndex):
            lvl0 = df.columns.get_level_values(0)
            if "Close" in lvl0:
                sub = df.loc[:, ("Close",)]
                close_s = sub.iloc[:, 0] if getattr(sub, "ndim", 1) > 1 else sub
            else:
                close_s = df.iloc[:, 0]
        else:
            close_s = df["Close"] if "Close" in getattr(df, "columns", []) else df.iloc[:, 0]

        # Ensure it's a Series-like
        if getattr(close_s, "ndim", 1) > 1:
            close_s = close_s.iloc[:, 0]

        close = float(close_s.iloc[-1]) if len(close_s) else 0.0
        ma50 = float(close_s.rolling(50).mean().iloc[-1]) if len(close_s) >= 50 else 0.0
        ma200 = float(close_s.rolling(200).mean().iloc[-1]) if len(close_s) >= 200 else 0.0

        # 20 trading days return ~= 21 points diff (today vs 20 sessions ago)
        if len(close_s) >= 21:
            prev = float(close_s.iloc[-21])
            ret_20d = (close / prev - 1.0) if prev else 0.0
        else:
            ret_20d = 0.0

        return {"close": close, "ma50": ma50, "ma200": ma200, "ret_20d": ret_20d}

    except Exception as e:
        # Fail-safe
        try:
            logger.warning("compute_metrics failed for %s: %s", label, e)
        except Exception:
            pass
        return {"close": 0.0, "ma50": 0.0, "ma200": 0.0, "ret_20d": 0.0}

    close = float(close_series.iloc[-1])
    ma50 = float(close_series.rolling(50).mean().iloc[-1])
    ma200 = float(close_series.rolling(200).mean().iloc[-1])

    # ret_20d: compare last close vs close 20 trading days ago
    if len(close_series) < 21:
        ret_20d = 0.0
    else:
        prev = float(close_series.iloc[-21])
        ret_20d = (close / prev - 1.0) if prev else 0.0

    return {"close": close, "ma50": ma50, "ma200": ma200, "ret_20d": ret_20d}

def _last_close(df) -> float:
    """
    Return last Close as float (robuste yfinance: MultiIndex columns, Series/scalar).
    """
    try:
        import pandas as pd  # type: ignore
        if df is None or len(df) == 0:
            return 0.0

        # Select a "Close" series
        close_series = None
        if hasattr(df, "columns") and isinstance(getattr(df, "columns"), pd.MultiIndex):
            # yfinance peut retourner MultiIndex (level0=OHLC, level1=ticker)
            lvl0 = df.columns.get_level_values(0)
            if "Close" in lvl0:
                sub = df.loc[:, ("Close",)]
                # sub peut être DataFrame (multi tickers) -> prendre 1ère colonne
                close_series = sub.iloc[:, 0] if hasattr(sub, "iloc") and getattr(sub, "ndim", 1) > 1 else sub
            else:
                close_series = df.iloc[:, 0]
        else:
            if hasattr(df, "__getitem__") and "Close" in getattr(df, "columns", []):
                close_series = df["Close"]
            else:
                close_series = df.iloc[:, 0]

        # Last value
        v = close_series.iloc[-1]

        # v peut être un scalar numpy/pandas
        try:
            return float(v)
        except Exception:
            pass

        # v peut être une Series (cas multi tickers)
        if hasattr(v, "iloc"):
            try:
                return float(v.iloc[0])
            except Exception:
                return 0.0

        # fallback
        if isinstance(v, (list, tuple)) and len(v) > 0:
            try:
                return float(v[0])
            except Exception:
                return 0.0

        return 0.0
    except Exception:
        return 0.0




def build_snapshot() -> Dict[str, Any]:
    """
    Fetch:
      - VIX: ^VIX (last close)
      - QQQ: QQQ (close + MA50 + MA200 + ret_20d)
      - SPY: SPY (close + MA50 + MA200 + ret_20d)

    Breadth: None for now.
    Robustness:
      - On error: reuse existing snapshot if present (refresh ts)
      - Else: safe default
    """
    try:
        import yfinance as yf  # type: ignore
        import pandas as pd  # noqa: F401

        # Download enough history for MA200 (use 1y to be safe)
        qqq_df = yf.download("QQQ", period="1y", interval="1d", progress=False, auto_adjust=False)
        spy_df = yf.download("SPY", period="1y", interval="1d", progress=False, auto_adjust=False)
        vix_df = yf.download("^VIX", period="1mo", interval="1d", progress=False, auto_adjust=False)

        qqq = _compute_metrics(qqq_df, "QQQ")
        spy = _compute_metrics(spy_df, "SPY")
        vix_close = _last_close(vix_df)

        snap = {
            "ts": _utc_now(),
            "vix": vix_close,
            "qqq": qqq,
            "spy": spy,
            "breadth": {"pct_above_ma200": None},
            "status": "ok",
            "source": "yfinance",
        }
        return snap

    except Exception as e:
        logger.warning("market_snapshot_builder failed (yfinance): %s", e)

        existing = _load_json(OUT)
        if existing:
            existing["ts"] = _utc_now()
            existing["status"] = existing.get("status") or "ok"
            existing["source"] = "yfinance(reuse_last)"
            existing["reason"] = f"fallback_reuse_last: {e}"
            return existing

        return _safe_default("default", f"yfinance_error: {e}")


def run() -> Dict[str, Any]:
    snap = build_snapshot()
    _write_json(OUT, snap)
    logger.info(
        "✅ market_snapshot written: %s status=%s vix=%.2f qqq_close=%.2f spy_close=%.2f",
        OUT,
        snap.get("status"),
        float(snap.get("vix") or 0.0),
        float((snap.get("qqq") or {}).get("close") or 0.0),
        float((snap.get("spy") or {}).get("close") or 0.0),
    )
    return snap


if __name__ == "__main__":
    run()
