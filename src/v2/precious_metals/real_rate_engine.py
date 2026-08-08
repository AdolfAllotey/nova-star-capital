from src.v2.precious_metals.metals_utils import (
    load_json_strict,
    require_finite_number,
    require_mapping,
    save_json,
)


def run_real_rate_engine(input_path, output_path):
    data = load_json_strict(input_path)
    rates = require_mapping(data, "real_rates")

    us_10y_real = require_finite_number(
        rates,
        "us_10y_real",
    )
    trend_1m = require_finite_number(
        rates,
        "real_rate_trend_1m",
    )

    if us_10y_real <= 1.0 and trend_1m <= 0:
        signal = "real_rates_bullish_gold"
        score = 0.85
    elif us_10y_real <= 1.75:
        signal = "real_rates_neutral_supportive"
        score = 0.6
    else:
        signal = "real_rates_headwind"
        score = 0.3

    output = {
        "engine": "real_rate_engine",
        "signal": signal,
        "score": score,
        "details": {
            "us_10y_real": us_10y_real,
            "real_rate_trend_1m": trend_1m,
        },
        "input_validation": "strict_fail_closed",
    }

    save_json(output, output_path)
    return output
