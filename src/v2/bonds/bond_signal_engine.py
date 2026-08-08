from src.v2.bonds.bond_utils import load_json, save_json


def run_bond_signal_engine(data_dir, output_path):

    rate = load_json(f"{data_dir}/rate_signal.json")
    infl = load_json(f"{data_dir}/inflation_signal.json")
    curve = load_json(f"{data_dir}/curve_signal.json")
    recession = load_json(f"{data_dir}/recession_signal.json")
    duration = load_json(f"{data_dir}/duration_signal.json")
    credit = load_json(f"{data_dir}/credit_signal.json")
    liquidity = load_json(f"{data_dir}/liquidity_signal.json")
    vol = load_json(f"{data_dir}/bond_vol_signal.json")

    scores = [
        rate.get("score", 0.5),
        infl.get("score", 0.5),
        curve.get("score", 0.5),
        recession.get("score", 0.5),
        duration.get("score", 0.5),
        credit.get("score", 0.5),
        liquidity.get("score", 0.5),
        vol.get("score", 0.5),
    ]

    bond_macro_score = sum(scores) / len(scores)
    confidence = round(0.60 + abs(bond_macro_score - 0.5), 4)

    if bond_macro_score > 0.7:
        target_exposure = 0.30
        regime = "strong_macro_defensive"
    elif bond_macro_score > 0.6:
        target_exposure = 0.22
        regime = "macro_defensive"
    elif bond_macro_score > 0.5:
        target_exposure = 0.15
        regime = "neutral_defensive"
    else:
        target_exposure = 0.08
        regime = "defensive_light"

    duration_target = duration.get("duration_target", "intermediate")

    if duration_target == "short":
        allocation = {"SHY": 0.60, "IEF": 0.25, "TLT": 0.05, "LQD": 0.10}
    elif duration_target == "long":
        allocation = {"SHY": 0.10, "IEF": 0.35, "TLT": 0.40, "LQD": 0.15}
    else:
        allocation = {"SHY": 0.20, "IEF": 0.45, "TLT": 0.20, "LQD": 0.15}

    if credit.get("signal") == "credit_stress":
        allocation["LQD"] = 0.05
        allocation["IEF"] += 0.05
        allocation["SHY"] += 0.05

    total = sum(allocation.values())
    allocation = {k: round(v / total, 4) for k, v in allocation.items()}

    output = {
        "brick": "bonds",
        "regime": regime,
        "bond_macro_score": round(bond_macro_score, 4),
        "target_exposure": target_exposure,
        "duration_target": duration_target,
        "confidence": confidence,
        "allocation": allocation,
        "drivers": {
            "rate_signal": rate.get("signal", "unknown"),
            "inflation_signal": infl.get("signal", "unknown"),
            "curve_signal": curve.get("signal", "unknown"),
            "recession_signal": recession.get("signal", "unknown"),
            "credit_signal": credit.get("signal", "unknown"),
            "liquidity_signal": liquidity.get("signal", "unknown"),
            "bond_vol_signal": vol.get("signal", "unknown")
        },
        "risk_flags": {
            "duration_risk": "medium" if duration_target == "long" else "low",
            "credit_risk": "medium" if allocation.get("LQD", 0) > 0.10 else "low",
            "volatility_risk": "medium" if vol.get("signal") == "vol_elevated" else (
                "high" if vol.get("signal") == "vol_stress" else "low"
            )
        },
        "execution_mode": "signal_only"
    }

    save_json(output, output_path)
    return output
