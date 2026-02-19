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
    """
    df: pandas.DataFrame with 'Close'
    """
    close_series = df["Close"].dropna()
    if len(close_series) < 220:
        # need ~200 days for ma200 + buffer
        raise ValueError(f"{label}: not enough data points ({len(close_series)})")

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

        vix_close = float(vix_df["Close"].dropna().iloc[-1]) if len(vix_df) and "Close" in vix_df else 0.0

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
