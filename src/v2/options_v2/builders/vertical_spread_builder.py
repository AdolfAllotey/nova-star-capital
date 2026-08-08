from datetime import datetime, timezone
from typing import Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_vertical_spread(signal: Dict[str, Any], vol_context: Dict[str, Any]) -> Dict[str, Any]:
    ticker = signal["ticker"]
    spot = float(signal.get("spot", 0.0))

    buy_strike = round(spot * 1.00, 2)
    sell_strike = round(spot * 1.05, 2)
    expiry_days = 45

    estimated_debit = round(spot * 0.015, 2)
    width = round(sell_strike - buy_strike, 2)
    max_profit = round((width - estimated_debit) * 100, 2)
    max_loss = round(estimated_debit * 100, 2)

    return {
        "ts": utc_now_iso(),
        "strategy": "vertical_spread",
        "spread_type": "bull_call_spread",
        "ticker": ticker,
        "underlying_spot": spot,
        "buy_strike": buy_strike,
        "sell_strike": sell_strike,
        "expiry_days": expiry_days,
        "estimated_debit_per_share": estimated_debit,
        "contract_count": 1,
        "max_profit": max_profit,
        "max_loss": max_loss,
        "vol_context": vol_context,
        "reason": "defined_risk_directional_trade",
    }
