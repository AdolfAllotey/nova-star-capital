from .bond_utils import load_json, save_json


def run_credit_spread_engine(input_path, output_path):
    data = load_json(input_path)
    credit = data.get("credit", {})

    ig = credit.get("ig_spread", 0)
    trend = credit.get("spread_trend_1m", 0)

    if ig < 1.5 and trend <= 0:
        signal = "credit_stable"
        score = 0.7
    elif ig < 2.5:
        signal = "credit_caution"
        score = 0.5
    else:
        signal = "credit_stress"
        score = 0.3

    output = {
        "engine": "credit_spread_engine",
        "signal": signal,
        "score": score
    }

    save_json(output, output_path)
    return output
