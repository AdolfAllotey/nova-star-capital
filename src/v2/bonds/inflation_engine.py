from .bond_utils import load_json, save_json


def run_inflation_engine(input_path, output_path):
    data = load_json(input_path)
    infl = data.get("inflation", {})

    cpi = infl.get("cpi_yoy", 0)
    trend = infl.get("inflation_trend_3m", 0)

    if cpi < 2.5 and trend < 0:
        signal = "disinflation_supportive"
        score = 0.8
    elif cpi > 3:
        signal = "inflation_headwind"
        score = 0.3
    else:
        signal = "neutral"
        score = 0.5

    output = {
        "engine": "inflation_engine",
        "signal": signal,
        "score": score
    }

    save_json(output, output_path)
    return output
