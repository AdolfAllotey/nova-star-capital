from datetime import datetime, timezone
from typing import Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_covered_call(position: Dict[str, Any], vol_context: Dict[str, Any]) -> Dict[str, Any]:
    ticker = position["ticker"]
    spot = float(position.get("current_price", position.get("avg_price", 0.0)))
    quantity = int(position.get("quantity", 0))

    strike = round(spot * 1.05, 2)
    expiry_days = 30
    estimated_premium = round(spot * 0.02, 2)

    return {
        "ts": utc_now_iso(),
        "strategy": "covered_call",
        "ticker": ticker,
        "underlying_spot": spot,
        "strike": strike,
        "expiry_days": expiry_days,
        "estimated_premium_per_share": estimated_premium,
        "contract_count": max(quantity // 100, 0),
        "max_profit_profile": "premium_plus_upside_until_strike",
        "max_loss_profile": "equity_downside_less_premium",
        "vol_context": vol_context,
        "reason": "income_overlay_on_existing_equity_position",
    }
