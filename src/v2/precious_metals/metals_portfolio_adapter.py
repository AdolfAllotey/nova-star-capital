from pathlib import Path

from src.v2.precious_metals.metals_utils import load_json, save_json


DEFAULT_DATA_DIR = Path("/opt/nsc/data/preprod/metals")


def clamp(value, low, high):
    return max(low, min(high, value))


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def compute_dynamic_metals_confidence(signal: dict, data_dir: Path = DEFAULT_DATA_DIR):
    inflation = load_json(str(data_dir / "inflation_signal.json"))
    real_rates = load_json(str(data_dir / "real_rate_signal.json"))
    stress = load_json(str(data_dir / "systemic_stress_signal.json"))
    usd = load_json(str(data_dir / "usd_signal.json"))

    inflation_score = _safe_float(inflation.get("score"), 0.0)
    real_rate_score = _safe_float(real_rates.get("score"), 0.0)
    stress_score = _safe_float(stress.get("score"), 0.0)
    usd_score = _safe_float(usd.get("score"), 0.0)
    macro_score = _safe_float(signal.get("metals_macro_score"), 0.0)

    weighted_score = (
        inflation_score * 0.25
        + real_rate_score * 0.25
        + stress_score * 0.30
        + usd_score * 0.10
        + macro_score * 0.10
    )

    regime = str(signal.get("regime", "unknown")).lower()
    regime_bonus = 0.04 if regime in {"systemic_hedge_active", "strong_systemic_hedge"} else 0.0

    risk_flags = signal.get("risk_flags", {}) if isinstance(signal, dict) else {}
    gold_vol = str(risk_flags.get("gold_volatility_risk", "unknown")).lower()
    silver_vol = str(risk_flags.get("silver_volatility_risk", "unknown")).lower()

    vol_penalty = 0.0
    if gold_vol == "high":
        vol_penalty += 0.04
    if silver_vol == "high":
        vol_penalty += 0.03
    elif silver_vol == "medium":
        vol_penalty += 0.01

    confidence = clamp(0.30 + weighted_score * 0.65 + regime_bonus - vol_penalty, 0.35, 0.92)

    return round(confidence, 4), {
        "method": "weighted_macro_metals_scores",
        "inflation_score": round(inflation_score, 4),
        "real_rate_score": round(real_rate_score, 4),
        "systemic_stress_score": round(stress_score, 4),
        "usd_score": round(usd_score, 4),
        "metals_macro_score": round(macro_score, 4),
        "weighted_score": round(weighted_score, 4),
        "regime_bonus": round(regime_bonus, 4),
        "vol_penalty": round(vol_penalty, 4),
        "gold_volatility_risk": gold_vol,
        "silver_volatility_risk": silver_vol,
    }


def export_metals_signal_to_portfolio_input(signal_path, output_path):
    signal = load_json(signal_path)
    data_dir = Path(signal_path).parent

    confidence, confidence_details = compute_dynamic_metals_confidence(signal, data_dir)

    drivers = signal.get("drivers", {})
    if not isinstance(drivers, dict):
        drivers = {}
    drivers = {
        **drivers,
        "confidence_details": confidence_details,
    }

    payload = {
        "brick": "precious_metals",
        "enabled": True,
        "portfolio_role": "systemic_hedge",
        "signal_type": "allocation_proposal",
        "target_weight": signal.get("target_exposure", 0.0),
        "confidence": confidence,
        "regime": signal.get("regime", "unknown"),
        "allocation": signal.get("allocation", {}),
        "drivers": drivers,
        "risk_flags": signal.get("risk_flags", {}),
        "inertia_profile": signal.get("inertia_profile", {}),
        "execution_mode": signal.get("execution_mode", "signal_only"),
        "funding_pool": "ibkr_pool",
        "source_file": signal_path
    }

    save_json(payload, output_path)
    return payload


if __name__ == "__main__":
    result = export_metals_signal_to_portfolio_input(
        "/opt/nsc/data/preprod/metals/metals_signal.json",
        "/opt/nsc/data/preprod/portfolio/inputs/precious_metals_portfolio_input.json"
    )
    print(result)
