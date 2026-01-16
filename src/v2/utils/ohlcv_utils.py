from __future__ import annotations

from typing import Any, Dict, List
from src.v2.utils.logger import get_logger

logger = get_logger("ohlcv_utils")

def ohlcv_v2_to_legacy_rows(raw: Any, max_points: int = 260) -> Any:
    """
    Convertit ohlcv_combined.json v2:
      {timestamp, env, assets:[{symbol, candles:[{open,high,low,close,volume,ts}, ...]}]}
    -> format legacy:
      { "BTCUSDT":[{"open":..,"high":..,"low":..,"close":..,"volume":..,"ts":..}, ...], ... }

    Si ce n'est pas du v2, retourne raw inchangé (compat).
    """
    if not isinstance(raw, dict):
        return raw

    assets = raw.get("assets")
    if not isinstance(assets, list):
        return raw

    def _f(x):
        try:
            return float(x)
        except Exception:
            return None

    def _i(x):
        try:
            return int(x)
        except Exception:
            return None

    out: Dict[str, List[dict]] = {}

    for a in assets:
        if not isinstance(a, dict):
            continue
        sym = a.get("symbol")
        candles = a.get("candles")
        if not isinstance(sym, str) or not isinstance(candles, list):
            continue

        rows = []
        for c in candles[-max_points:]:
            if not isinstance(c, dict):
                continue

            close = _f(c.get("close") if c.get("close") is not None else c.get("c"))
            if close is None or close <= 0:
                continue

            row = {
                "ts": _i(c.get("ts")),
                "open": _f(c.get("open")),
                "high": _f(c.get("high")),
                "low": _f(c.get("low")),
                "close": close,
                "volume": _f(c.get("volume")),
            }
            # garde au moins close+ts (les autres peuvent être None selon le producer)
            rows.append(row)

        if len(rows) >= 6:
            out[sym] = rows

    if not out:
        logger.warning("[ohlcv_utils] v2 assets présents mais aucune série exploitable (max_points=%s).", max_points)
        return raw

    return out
