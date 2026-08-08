from pathlib import Path

from src.v2.bonds.bond_utils import load_json, save_json


DEFAULT_DATA_DIR = Path("/opt/nsc/data/preprod/bonds")


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def compute_dynamic_bond_confidence(bond_signal: dict, data_dir: Path = DEFAULT_DATA_DIR):
    rate = load_json(str(data_dir / "rate_signal.json"))
    inflation = load_json(str(data_dir / "inflation_signal.json"))
    curve = load_json(str(data_dir / "curve_signal.json"))
    recession = load_json(str(data_dir / "recession_signal.json"))
    credit = load_json(str(data_dir / "credit_signal.json"))
    liquidity = load_json(str(data_dir / "liquidity_signal.json"))
    bond_vol = load_json(str(data_dir / "bond_vol_signal.json"))

    rate_score = safe_float(rate.get("score"), 0.0)
    inflation_score = safe_float(inflation.get("score"), 0.0)
    curve_score = safe_float(curve.get("score"), 0.0)
    recession_score = safe_float(recession.get("score"), 0.0)
    credit_score = safe_float(credit.get("score"), 0.0)
    liquidity_score = safe_float(liquidity.get("score"), 0.0)
    vol_score = safe_float(bond_vol.get("score"), 0.0)
    macro_score = safe_float(bond_signal.get("bond_macro_score"), 0.0)

    weighted_score = (
        rate_score * 0.20
        + inflation_score * 0.15
        + curve_score * 0.10
        + recession_score * 0.10
        + credit_score * 0.15
        + liquidity_score * 0.10
        + vol_score * 0.10
        + macro_score * 0.10
    )

    risk_flags = bond_signal.get("risk_flags", {}) if isinstance(bond_signal, dict) else {}

    duration_risk = str(risk_flags.get("duration_risk", "unknown")).lower()
    credit_risk = str(risk_flags.get("credit_risk", "unknown")).lower()
    volatility_risk = str(risk_flags.get("volatility_risk", "unknown")).lower()

    risk_penalty = 0.0
    if duration_risk == "high":
        risk_penalty += 0.04
    elif duration_risk == "medium":
        risk_penalty += 0.02

    if credit_risk == "high":
        risk_penalty += 0.04
    elif credit_risk == "medium":
        risk_penalty += 0.02

    if volatility_risk == "high":
        risk_penalty += 0.04
    elif volatility_risk == "medium":
        risk_penalty += 0.02

    regime = str(bond_signal.get("regime", "unknown")).lower()
    regime_bonus = 0.03 if regime in {"macro_defensive", "neutral_defensive"} else 0.0

    confidence = clamp(0.32 + weighted_score * 0.62 + regime_bonus - risk_penalty, 0.35, 0.90)

    return round(confidence, 4), {
        "method": "weighted_macro_bond_scores",
        "rate_score": round(rate_score, 4),
        "inflation_score": round(inflation_score, 4),
        "curve_score": round(curve_score, 4),
        "recession_score": round(recession_score, 4),
        "credit_score": round(credit_score, 4),
        "liquidity_score": round(liquidity_score, 4),
        "bond_vol_score": round(vol_score, 4),
        "bond_macro_score": round(macro_score, 4),
        "weighted_score": round(weighted_score, 4),
        "regime_bonus": round(regime_bonus, 4),
        "risk_penalty": round(risk_penalty, 4),
        "duration_risk": duration_risk,
        "credit_risk": credit_risk,
        "volatility_risk": volatility_risk,
    }


def export_bond_signal_to_portfolio_input(
    bond_signal_path: str,
    output_path: str
) -> dict:
    bond_signal = load_json(bond_signal_path)
    data_dir = Path(bond_signal_path).parent

    allocation = bond_signal.get("allocation", {})
    target_exposure = bond_signal.get("target_exposure", 0.0)
    confidence, confidence_details = compute_dynamic_bond_confidence(bond_signal, data_dir)

    drivers = bond_signal.get("drivers", {})
    if not isinstance(drivers, dict):
        drivers = {}
    drivers = {
        **drivers,
        "confidence_details": confidence_details,
    }

    payload = {
        "brick": "bonds",
        "enabled": True,
        "portfolio_role": "macro_stabilizer",
        "signal_type": "allocation_proposal",
        "target_weight": target_exposure,
        "confidence": confidence,
        "regime": bond_signal.get("regime", "unknown"),
        "duration_target": bond_signal.get("duration_target", "intermediate"),
        "allocation": allocation,
        "drivers": drivers,
        "risk_flags": bond_signal.get("risk_flags", {}),
        "inertia_profile": {
            "rebalance_frequency": "low",
            "max_weight_change_per_cycle": 0.02,
            "min_threshold_to_rebalance": 0.03
        },
        "execution_mode": bond_signal.get("execution_mode", "signal_only"),
        "funding_pool": "ibkr_pool",
        "source_file": bond_signal_path
    }

    save_json(payload, output_path)
    return payload


if __name__ == "__main__":
    result = export_bond_signal_to_portfolio_input(
        "/opt/nsc/data/preprod/bonds/bond_signal.json",
        "/opt/nsc/data/preprod/portfolio/inputs/bonds_portfolio_input.json"
    )
    print(result)
