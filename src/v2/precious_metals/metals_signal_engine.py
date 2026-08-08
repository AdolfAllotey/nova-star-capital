from src.v2.precious_metals.metals_utils import load_json, save_json


def run_metals_signal_engine(data_dir, output_path):
    inflation = load_json(f"{data_dir}/inflation_signal.json")
    real_rates = load_json(f"{data_dir}/real_rate_signal.json")
    stress = load_json(f"{data_dir}/systemic_stress_signal.json")
    usd = load_json(f"{data_dir}/usd_signal.json")

    inflation_score = inflation.get("score", 0.5)
    real_rate_score = real_rates.get("score", 0.5)
    stress_score = stress.get("score", 0.5)
    usd_score = usd.get("score", 0.5)

    metals_macro_score = round(
        inflation_score * 0.25 +
        real_rate_score * 0.30 +
        stress_score * 0.30 +
        usd_score * 0.15,
        4
    )

    if metals_macro_score >= 0.75:
        regime = "strong_systemic_hedge"
        target_exposure = 0.10
    elif metals_macro_score >= 0.60:
        regime = "systemic_hedge_active"
        target_exposure = 0.08
    elif metals_macro_score >= 0.45:
        regime = "pre_hedge"
        target_exposure = 0.04
    else:
        regime = "inactive"
        target_exposure = 0.00

    confidence = round(0.60 + abs(metals_macro_score - 0.5), 4)

    silver_allowed = (
        stress.get("signal") in {"stress_elevated", "stress_high"}
        and inflation.get("score", 0.0) >= 0.6
    )

    if target_exposure == 0.0:
        allocation = {"GLD": 1.0}
    elif silver_allowed and target_exposure >= 0.08:
        allocation = {"GLD": 0.80, "SLV": 0.20}
    else:
        allocation = {"GLD": 1.0}

    output = {
        "brick": "precious_metals",
        "regime": regime,
        "metals_macro_score": metals_macro_score,
        "target_exposure": target_exposure,
        "confidence": confidence,
        "allocation": allocation,
        "drivers": {
            "inflation_signal": inflation.get("signal", "unknown"),
            "real_rate_signal": real_rates.get("signal", "unknown"),
            "systemic_stress_signal": stress.get("signal", "unknown"),
            "usd_signal": usd.get("signal", "unknown")
        },
        "risk_flags": {
            "gold_volatility_risk": "low",
            "silver_volatility_risk": "medium" if "SLV" in allocation else "low"
        },
        "inertia_profile": {
            "rebalance_frequency": "low",
            "max_weight_change_per_cycle": 0.02,
            "min_threshold_to_rebalance": 0.03
        },
        "execution_mode": "signal_only"
    }

    save_json(output, output_path)
    return output
