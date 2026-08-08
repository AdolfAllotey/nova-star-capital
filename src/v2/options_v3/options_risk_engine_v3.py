import json


def apply_risk_filters(signals, context, portfolio_state, offensive_positions):
    """
    Apply risk filters on options signals
    """

    validated = []
    rejected = []

    max_options_exposure = 0.15  # 15% max
    current_options_exposure = portfolio_state.get("options_exposure", 0)

    portfolio_bias = context.get("portfolio_bias")
    regime = context.get("market_regime")

    for sig in signals:
        ticker = sig.get("ticker")
        strategy = sig.get("strategy")

        reason = None

        # 🔴 1. Exposure cap
        if current_options_exposure >= max_options_exposure:
            reason = "OPTIONS_EXPOSURE_LIMIT"

        # 🔴 2. Duplicate with offensive
        elif ticker in offensive_positions:
            reason = "DUPLICATE_OFFENSIVE_POSITION"

        # 🔴 3. Regime conflict
        elif regime == "RISK_OFF" and "call" in strategy:
            reason = "REGIME_CONFLICT"

        # 🔴 4. Portfolio bias conflict
        elif portfolio_bias == "LONG_TECH" and ticker not in ["NVDA", "AAPL", "MSFT", "AMZN", "META"]:
            reason = "PORTFOLIO_BIAS_CONFLICT"

        if reason:
            rejected.append({
                "signal": sig,
                "reason": reason
            })
        else:
            validated.append(sig)

    return validated, rejected


def build_risk_summary(validated, rejected):
    return {
        "validated_count": len(validated),
        "rejected_count": len(rejected),
        "top_rejection_reason": (
            max(
                [r["reason"] for r in rejected],
                key=[r["reason"] for r in rejected].count
            )
            if rejected else None
        )
    }


def save_risk_output(validated, rejected, path):
    with open(path, "w") as f:
        json.dump({
            "validated": validated,
            "rejected": rejected
        }, f, indent=2)
