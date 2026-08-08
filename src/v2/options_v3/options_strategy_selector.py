import json
from datetime import datetime


def select_strategy(context):
    """
    Select best options strategy based on context
    """

    regime = context.get("market_regime")
    vol = context.get("volatility_regime")
    hedge_needed = context.get("hedge_needed", False)
    theta_opportunity = context.get("theta_opportunity", False)

    # Core logic (simple + explicable)
    if hedge_needed:
        strategy = "long_put"
        reason = "Hedge needed due to RISK_OFF regime"

    elif regime == "RISK_ON":
        strategy = "bull_call_spread"
        reason = "Bullish regime detected"

    elif vol == "HIGH" and theta_opportunity:
        strategy = "short_premium"
        reason = "High volatility, premium selling opportunity"

    else:
        strategy = "neutral_spread"
        reason = "No strong directional signal"

    return {
        "ts": datetime.utcnow().isoformat(),
        "strategy": strategy,
        "reason": reason,
        "confidence": build_confidence(context, strategy)
    }


def build_confidence(context, strategy):
    """
    Simple confidence scoring (0–1)
    """

    score = 0.5

    if context.get("market_regime") == "RISK_ON" and strategy == "bull_call_spread":
        score += 0.2

    if context.get("volatility_regime") == "HIGH":
        score += 0.1

    if context.get("portfolio_bias") == "LONG_TECH":
        score += 0.1

    return min(score, 0.95)


def save_strategy(strategy, path):
    with open(path, "w") as f:
        json.dump(strategy, f, indent=2)
