from datetime import datetime, timezone
from typing import Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_cash_secured_put(signal: Dict[str, Any], vol_context: Dict[str, Any]) -> Dict[str, Any]:
    ticker = signal["ticker"]
    spot = float(signal.get("spot", 0.0))

    strike = round(spot * 0.95, 2)
    expiry_days = 30
    estimated_premium = round(spot * 0.025, 2)
    required_cash = round(strike * 100, 2)

    return {
        "ts": utc_now_iso(),
        "strategy": "cash_secured_put",
        "ticker": ticker,
        "underlying_spot": spot,
        "strike": strike,
        "expiry_days": expiry_days,
        "estimated_premium_per_share": estimated_premium,
        "contract_count": 1,
        "cash_required": required_cash,
        "max_profit_profile": "premium_received",
        "max_loss_profile": "assignment_risk_down_to_zero_less_premium",
        "vol_context": vol_context,
        "reason": "paid_entry_on_watchlist_name",
    }
