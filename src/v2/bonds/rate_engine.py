from .bond_utils import load_json, save_json


def run_rate_engine(input_path, output_path):
    data = load_json(input_path)
    rates = data.get("rates", {})

    us10y = rates.get("us_10y", 0)

    if us10y < 3.8:
        signal = "bullish_bonds"
        score = 0.8
        trend = "down"
    elif us10y > 4.2:
        signal = "bearish_bonds"
        score = 0.3
        trend = "up"
    else:
        signal = "neutral_bonds"
        score = 0.5
        trend = "flat"

    output = {
        "engine": "rate_engine",
        "signal": signal,
        "score": score,
        "details": {
            "rate_trend": trend
        }
    }

    save_json(output, output_path)
    return output
