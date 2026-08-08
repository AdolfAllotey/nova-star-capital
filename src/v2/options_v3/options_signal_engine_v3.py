import json
from datetime import datetime


def generate_options_signals(context, strategy_payload, external_signals):
    """
    Generate options signals aligned with strategy + context
    """

    selected_strategy = strategy_payload.get("strategy")
    portfolio_bias = context.get("portfolio_bias")

    signals = []

    for sig in external_signals:
        ticker = sig.get("ticker")
        direction = sig.get("direction", "neutral")

        # 🔹 Alignement directionnel simple
        if selected_strategy == "bull_call_spread" and direction != "bullish":
            continue

        if selected_strategy == "long_put" and direction != "bearish":
            continue

        # 🔹 Filtre portfolio (éviter incohérences)
        if portfolio_bias == "LONG_TECH" and ticker not in ["NVDA", "AAPL", "MSFT", "AMZN", "META"]:
            continue

        signals.append({
            "ts": datetime.utcnow().isoformat(),
            "ticker": ticker,
            "strategy": selected_strategy,
            "direction": direction,
            "source": sig.get("source", "external"),
            "confidence": build_signal_confidence(sig, strategy_payload)
        })

    return signals


def build_signal_confidence(signal, strategy_payload):
    """
    Combine signal + strategy confidence
    """
    base = signal.get("confidence", 0.5)
    strat = strategy_payload.get("confidence", 0.5)

    return round(min((base + strat) / 2, 0.95), 2)


def save_signals(signals, path):
    with open(path, "w") as f:
        json.dump(signals, f, indent=2)


def load_external_signals(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []
