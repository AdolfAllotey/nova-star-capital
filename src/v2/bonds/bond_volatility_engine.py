from .bond_utils import load_json, save_json


def run_bond_volatility_engine(input_path, output_path):
    data = load_json(input_path)
    vol = data.get("volatility", {})

    move = vol.get("move_index", 0)

    if move < 90:
        signal = "vol_low"
        score = 0.8
    elif move < 120:
        signal = "vol_elevated"
        score = 0.5
    else:
        signal = "vol_stress"
        score = 0.3

    output = {
        "engine": "bond_volatility_engine",
        "signal": signal,
        "score": score
    }

    save_json(output, output_path)
    return output
