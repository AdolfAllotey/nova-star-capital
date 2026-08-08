from .bond_utils import load_json, save_json


def run_duration_engine(rate_path, inflation_path, vol_path, output_path):
    rate = load_json(rate_path)
    infl = load_json(inflation_path)
    vol = load_json(vol_path)

    rate_score = rate.get("score", 0.5)
    infl_score = infl.get("score", 0.5)
    vol_score = vol.get("score", 0.5)

    avg = round((rate_score + infl_score + vol_score) / 3, 4)

    if avg > 0.7:
        duration = "long"
    elif avg > 0.5:
        duration = "intermediate"
    else:
        duration = "short"

    output = {
        "engine": "duration_engine",
        "duration_target": duration,
        "score": avg
    }

    save_json(output, output_path)
    return output
