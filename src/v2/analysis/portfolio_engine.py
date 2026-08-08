"""
NSC Portfolio Engine
Orchestrates allocation across trading strategies.
"""

import json
from pathlib import Path

DATA_DIR = Path("/opt/nsc/data/preprod/analysis")

DEFAULT_PORTFOLIO = {
    "crypto": {
        "target_weight": 0.10,
        "status": "ACTIVE"
    },
    "equities_offensive": {
        "target_weight": 0.15,
        "status": "ACTIVE"
    },
    "equities_defensive": {
        "target_weight": 0.20,
        "status": "ACTIVE"
    },
    "long_term": {
        "target_weight": 0.37,
        "status": "INACTIVE"
    },
    "options_us": {
        "target_weight": 0.18,
        "status": "INACTIVE"
    }
}


def _load_json(path: Path, default=None):
    try:
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _pick_number(payload, keys, default=0.0):
    if not isinstance(payload, dict):
        return float(default)
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return float(default)


def build_portfolio_state():
    portfolio = DEFAULT_PORTFOLIO.copy()

    # Defaults pour stabiliser l'UI
    portfolio["crypto"]["exposure"] = portfolio["crypto"]["target_weight"]
    portfolio["crypto"]["confidence"] = 0.0

    portfolio["equities_offensive"]["exposure"] = 0.0
    portfolio["equities_offensive"]["confidence"] = 0.0

    portfolio["equities_defensive"]["exposure"] = portfolio["equities_defensive"]["target_weight"]
    portfolio["equities_defensive"]["confidence"] = 0.0

    # ----- Equities Offensive -----
    offensive_exposure = _load_json(
        Path("/opt/nsc/app/data/equities_offensive/state/exposure_snapshot.json"),
        {}
    )
    portfolio["equities_offensive"]["exposure"] = _pick_number(
        offensive_exposure,
        ["total_notional_usd", "target_exposure", "gross_exposure", "net_exposure", "exposure"],
        0.0,
    )

    offensive_bundle = _load_json(
        Path("/opt/nsc/app/data/equities_offensive/ui/ui_bundle.json"),
        {}
    )
    if isinstance(offensive_bundle, dict):
        kpis = offensive_bundle.get("kpis", {})
        if isinstance(kpis, dict):
            portfolio["equities_offensive"]["confidence"] = _pick_number(
                kpis,
                ["regime_confidence", "confidence"],
                0.0,
            )

    # ----- Equities Defensive -----
    defensive_signal = _load_json(
        Path("/opt/nsc/app/src/v2/data/defensive/defensive_signal.json"),
        {}
    )
    portfolio["equities_defensive"]["exposure"] = _pick_number(
        defensive_signal,
        ["target_exposure", "exposure"],
        portfolio["equities_defensive"]["target_weight"],
    )
    portfolio["equities_defensive"]["confidence"] = _pick_number(
        defensive_signal,
        ["confidence"],
        0.0,
    )

    total_weight = sum(v["target_weight"] for v in portfolio.values())

    return {
        "portfolio": portfolio,
        "total_weight": total_weight
    }


def save_portfolio_state():
    state = build_portfolio_state()

    output = DATA_DIR / "portfolio_state.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        json.dump(state, f, indent=2)

    return state


if __name__ == "__main__":
    result = save_portfolio_state()
    print(json.dumps(result, indent=2))
