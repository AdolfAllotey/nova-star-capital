from src.v2.precious_metals.metals_utils import (
    load_json_strict,
    require_finite_number,
    require_mapping,
    save_json,
)


def run_inflation_hedge_engine(input_path, output_path):
    data = load_json_strict(input_path)
    inflation = require_mapping(data, "inflation")

    cpi = require_finite_number(
        inflation,
        "cpi_yoy",
    )
    trend = require_finite_number(
        inflation,
        "inflation_trend_3m",
    )
    credibility = require_finite_number(
        inflation,
        "central_bank_credibility_score",
        minimum=0.0,
        maximum=1.0,
    )

    if cpi >= 3.5 or (cpi >= 3.0 and trend >= 0):
        signal = "inflation_supportive"
        score = 0.8
    elif cpi >= 2.5 or credibility < 0.45:
        signal = "inflation_moderate_support"
        score = 0.6
    else:
        signal = "inflation_neutral"
        score = 0.35

    output = {
        "engine": "inflation_hedge_engine",
        "signal": signal,
        "score": score,
        "details": {
            "cpi_yoy": cpi,
            "inflation_trend_3m": trend,
            "central_bank_credibility_score": credibility,
        },
        "input_validation": "strict_fail_closed",
    }

    save_json(output, output_path)
    return output
