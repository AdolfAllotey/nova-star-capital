from src.v2.precious_metals.metals_utils import (
    load_json_strict,
    require_finite_number,
    require_mapping,
    save_json,
)


def run_systemic_stress_engine(input_path, output_path):
    data = load_json_strict(input_path)
    stress = require_mapping(data, "systemic_stress")

    stress_score = require_finite_number(
        stress,
        "stress_score",
        minimum=0.0,
        maximum=1.0,
    )
    liquidity_stress = require_finite_number(
        stress,
        "liquidity_stress",
        minimum=0.0,
        maximum=1.0,
    )
    banking_stress = require_finite_number(
        stress,
        "banking_stress",
        minimum=0.0,
        maximum=1.0,
    )

    composite = max(
        stress_score,
        liquidity_stress,
        banking_stress,
    )

    if composite >= 0.75:
        signal = "stress_high"
        score = 0.9
    elif composite >= 0.5:
        signal = "stress_elevated"
        score = 0.7
    elif composite >= 0.3:
        signal = "stress_moderate"
        score = 0.5
    else:
        signal = "stress_low"
        score = 0.25

    output = {
        "engine": "systemic_stress_engine",
        "signal": signal,
        "score": score,
        "details": {
            "stress_score": stress_score,
            "liquidity_stress": liquidity_stress,
            "banking_stress": banking_stress,
            "composite_stress": composite,
        },
        "input_validation": "strict_fail_closed",
    }

    save_json(output, output_path)
    return output
