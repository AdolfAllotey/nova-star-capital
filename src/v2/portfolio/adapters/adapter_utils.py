import json
from datetime import datetime


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(data, path):
    if not isinstance(data, dict):
        data = {"value": data}
    data["timestamp"] = datetime.utcnow().isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def build_portfolio_input_payload(
    *,
    brick: str,
    portfolio_role: str,
    funding_pool: str,
    signal: dict,
    target_weight_field: str = "target_exposure",
    allocation_field: str = "allocation",
    regime_field: str = "regime",
    confidence_field: str = "confidence",
    drivers_field: str = "drivers",
    risk_flags_field: str = "risk_flags",
    inertia_profile: dict | None = None,
    source_file: str = ""
) -> dict:
    return {
        "brick": brick,
        "enabled": True,
        "portfolio_role": portfolio_role,
        "signal_type": "allocation_proposal",
        "target_weight": float(signal.get(target_weight_field, 0.0) or 0.0),
        "confidence": float(signal.get(confidence_field, 0.0) or 0.0),
        "regime": signal.get(regime_field, "unknown"),
        "allocation": signal.get(allocation_field, {}),
        "drivers": signal.get(drivers_field, {}),
        "risk_flags": signal.get(risk_flags_field, {}),
        "inertia_profile": inertia_profile or {},
        "execution_mode": signal.get("execution_mode", "signal_only"),
        "funding_pool": funding_pool,
        "source_file": source_file,
    }
