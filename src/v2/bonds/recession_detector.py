from .bond_utils import load_json, save_json


def run_recession_detector(input_path, output_path):
    data = load_json(input_path)
    macro = data.get("macro", {})

    prob = macro.get("recession_probability", 0)

    if prob > 0.6:
        signal = "recession_risk_high"
        score = 0.85
    elif prob > 0.4:
        signal = "moderate"
        score = 0.6
    else:
        signal = "low"
        score = 0.3

    output = {
        "engine": "recession_detector",
        "signal": signal,
        "score": score
    }

    save_json(output, output_path)
    return output
