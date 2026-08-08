from datetime import datetime, timezone
from typing import Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_vol_regime(iv_rank: float) -> str:
    if iv_rank >= 60:
        return "high"
    if iv_rank <= 30:
        return "low"
    return "medium"


def classify_strategy_bias(iv_rank: float) -> str:
    if iv_rank >= 60:
        return "sell_vol"
    if iv_rank <= 30:
        return "buy_vol"
    return "neutral"


def analyze_volatility_context(
    volatility_data: Dict[str, Dict[str, Any]],
    governance: Dict[str, Any],
) -> Dict[str, Any]:
    results = {
        "ts": utc_now_iso(),
        "engine": "volatility_engine_v1",
        "tickers": {},
    }

    block_window = int(governance.get("event_block_window_days", 5))

    for ticker, data in volatility_data.items():
        iv = float(data.get("iv", 0.0))
        iv_rank = float(data.get("iv_rank", 0.0))
        hist_vol = float(data.get("historical_vol", 0.0))
        days_to_event = data.get("days_to_event")

        event_risk = False
        if isinstance(days_to_event, (int, float)) and days_to_event <= block_window:
            event_risk = True

        results["tickers"][ticker] = {
            "ticker": ticker,
            "iv": iv,
            "iv_rank": iv_rank,
            "historical_vol": hist_vol,
            "days_to_event": days_to_event,
            "vol_regime": classify_vol_regime(iv_rank),
            "strategy_bias": classify_strategy_bias(iv_rank),
            "event_risk": event_risk,
        }

    return results
