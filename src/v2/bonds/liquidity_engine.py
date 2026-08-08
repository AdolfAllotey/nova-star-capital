from .bond_utils import load_json, save_json


def run_liquidity_engine(input_path, output_path):
    data = load_json(input_path)
    liq = data.get("liquidity", {})

    fci = liq.get("financial_conditions_index", 0)

    if fci > 1:
        signal = "liquidity_tight"
        score = 0.3
    elif fci < 0:
        signal = "liquidity_supportive"
        score = 0.8
    else:
        signal = "neutral"
        score = 0.5

    output = {
        "engine": "liquidity_engine",
        "signal": signal,
        "score": score
    }

    save_json(output, output_path)
    return output
