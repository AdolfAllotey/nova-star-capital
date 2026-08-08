from src.v2.precious_metals.metals_utils import (
    load_json_strict,
    require_finite_number,
    require_mapping,
    save_json,
)


def run_usd_engine(input_path, output_path):
    data = load_json_strict(input_path)
    usd = require_mapping(data, "usd")

    dxy = require_finite_number(
        usd,
        "dxy",
        minimum=0.0,
    )
    dxy_trend_1m = require_finite_number(
        usd,
        "dxy_trend_1m",
    )

    if dxy <= 102 and dxy_trend_1m <= 0:
        signal = "usd_supportive"
        score = 0.75
    elif dxy <= 106:
        signal = "usd_neutral"
        score = 0.5
    else:
        signal = "usd_headwind_moderate"
        score = 0.3

    output = {
        "engine": "usd_engine",
        "signal": signal,
        "score": score,
        "details": {
            "dxy": dxy,
            "dxy_trend_1m": dxy_trend_1m,
        },
        "input_validation": "strict_fail_closed",
    }

    save_json(output, output_path)
    return output
