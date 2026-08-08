from .bond_utils import load_json, save_json


def run_yield_curve_engine(input_path, output_path):
    data = load_json(input_path)
    curve = data.get("yield_curve", {})

    spread = curve.get("2s10s", 0)

    if spread < -0.2:
        signal = "recessionary_curve"
        score = 0.8
    elif spread > 0.3:
        signal = "steepening_reflation"
        score = 0.4
    else:
        signal = "normal_curve"
        score = 0.5

    output = {
        "engine": "yield_curve_engine",
        "signal": signal,
        "score": score
    }

    save_json(output, output_path)
    return output
