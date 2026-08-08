from src.v2.portfolio.adapters.adapter_utils import load_json, save_json


import os
from pathlib import Path

ROOT = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

INPUT_PATH = str(ROOT / "defensive/defensive_signal.json")
STATE_PATH = str(ROOT / "defensive/defensive_state.json")
OUTPUT_PATH = str(ROOT / "portfolio/inputs/equities_defensive_portfolio_input.json")


def clamp(value, low, high):
    return max(low, min(high, value))


def _derive_regime(signal: dict, confidence: float) -> str:
    target_exposure = float(signal.get("target_exposure", 0.0) or 0.0)

    if target_exposure >= 0.18 and confidence >= 0.80:
        return "stabilization_active"
    if target_exposure >= 0.10:
        return "stabilization_moderate"
    return "stabilization_light"


def _build_allocation(signal: dict) -> dict:
    proposed_assets = signal.get("proposed_assets", [])
    allocation = {}

    if isinstance(proposed_assets, list) and proposed_assets:
        for asset in proposed_assets:
            ticker = asset.get("ticker")
            weight = asset.get("weight")
            if ticker is not None and weight is not None:
                allocation[ticker] = float(weight)

    return allocation


def compute_dynamic_defensive_confidence(signal: dict, state: dict):
    source_conf = float(signal.get("confidence", state.get("confidence", 0.0)) or 0.0)
    summary = signal.get("score_summary", {}) if isinstance(signal, dict) else {}

    selected_assets = int(summary.get("selected_assets_count", 0) or 0)
    constraints_ok = bool(summary.get("constraints_respected", False))
    beta = summary.get("portfolio_beta_estimate", state.get("portfolio_beta_estimate"))

    try:
        beta = float(beta)
    except Exception:
        beta = None

    target_exposure = float(signal.get("target_exposure", state.get("target_exposure", 0.0)) or 0.0)
    current_exposure = float(state.get("current_exposure_eur", 0.0) or 0.0)
    target_amount = float(state.get("target_amount_eur", 0.0) or 0.0)

    exposure_gap_ratio = 0.0
    if target_amount > 0:
        exposure_gap_ratio = abs(current_exposure - target_amount) / target_amount

    diversification_component = clamp(selected_assets / 10.0, 0.0, 1.0) * 0.08
    constraint_component = 0.06 if constraints_ok else -0.08
    beta_component = 0.05 if beta is not None and beta <= 0.75 else -0.03
    exposure_penalty = min(0.08, exposure_gap_ratio * 0.5)

    confidence = (
        source_conf * 0.82
        + diversification_component
        + constraint_component
        + beta_component
        - exposure_penalty
    )

    confidence = clamp(confidence, 0.45, 0.95)

    return round(confidence, 4), {
        "method": "source_plus_constraints_beta_exposure",
        "source_confidence": round(source_conf, 4),
        "selected_assets_count": selected_assets,
        "diversification_component": round(diversification_component, 4),
        "constraints_respected": constraints_ok,
        "constraint_component": round(constraint_component, 4),
        "portfolio_beta_estimate": beta,
        "beta_component": round(beta_component, 4),
        "target_exposure": target_exposure,
        "target_amount_eur": target_amount,
        "current_exposure_eur": current_exposure,
        "exposure_gap_ratio": round(exposure_gap_ratio, 6),
        "exposure_penalty": round(exposure_penalty, 4),
    }


def export_defensive_equities_to_portfolio_input(
    input_path: str = INPUT_PATH,
    state_path: str = STATE_PATH,
    output_path: str = OUTPUT_PATH
):
    signal = load_json(input_path)
    state = load_json(state_path)
    score_summary = signal.get("score_summary", {})

    allocation = _build_allocation(signal)
    confidence, confidence_details = compute_dynamic_defensive_confidence(signal, state)

    payload = {
        "brick": "equities_defensive",
        "enabled": True,
        "portfolio_role": "stabilization",
        "signal_type": "allocation_proposal",
        "target_weight": float(signal.get("target_exposure", 0.0) or 0.0),
        "confidence": confidence,
        "regime": _derive_regime(signal, confidence),
        "allocation": allocation,
        "drivers": {
            "mode": signal.get("mode", "unknown"),
            "reason": signal.get("reason", "unknown"),
            "selected_assets_count": score_summary.get("selected_assets_count", 0),
            "constraints_respected": score_summary.get("constraints_respected", False),
            "portfolio_beta_estimate": score_summary.get("portfolio_beta_estimate", None),
            "confidence_details": confidence_details,
        },
        "risk_flags": {
            "constraints_respected": score_summary.get("constraints_respected", False),
            "portfolio_beta_estimate": score_summary.get("portfolio_beta_estimate", None)
        },
        "inertia_profile": {
            "rebalance_frequency": "medium",
            "max_weight_change_per_cycle": 0.03,
            "min_threshold_to_rebalance": 0.03
        },
        "execution_mode": signal.get("execution_mode", "signal_only"),
        "funding_pool": "ibkr_pool",
        "source_file": input_path,
        "state_file": state_path,
    }

    save_json(payload, output_path)
    return payload


if __name__ == "__main__":
    result = export_defensive_equities_to_portfolio_input()
    print(result)
