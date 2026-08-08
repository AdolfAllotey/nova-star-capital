import json
from datetime import datetime

def build_options_context(global_data, portfolio_state, volatility_data):
    """
    Build macro + portfolio context for Options V3
    """

    regime = global_data.get("regime", "UNKNOWN")
    governance = global_data.get("governanceMode", "UNKNOWN")

    # Simple volatility interpretation
    iv_rank = volatility_data.get("iv_rank", 50)
    if iv_rank >= 60:
        vol_regime = "HIGH"
    elif iv_rank <= 30:
        vol_regime = "LOW"
    else:
        vol_regime = "MID"

    # Portfolio bias detection (simple v1)
    exposure = portfolio_state.get("exposure", {})
    tech_exposure = exposure.get("tech", 0)

    if tech_exposure > 0.5:
        bias = "LONG_TECH"
    else:
        bias = "BALANCED"

    context = {
        "ts": datetime.utcnow().isoformat(),
        "market_regime": regime,
        "governance_mode": governance,
        "volatility_regime": vol_regime,
        "portfolio_bias": bias,
        "exposure": exposure,
        "hedge_needed": regime == "RISK_OFF",
        "theta_opportunity": vol_regime == "HIGH"
    }

    return context


def save_context(context, path):
    with open(path, "w") as f:
        json.dump(context, f, indent=2)


def load_json(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default or {}
