#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime, UTC

BASE = Path("/opt/nsc/app/src/v2/data/portfolio")
INPUTS = BASE / "inputs"
TARGET = BASE / "portfolio_target.json"
AUDIT = BASE / "aggregator_audit.json"
OUTPUT = BASE / "aggregator_explainability.json"

BRICK_LABELS = {
    "bonds": "Bonds",
    "crypto": "Crypto",
    "equities_defensive": "Defensive Equities",
    "equities_offensive": "Offensive Equities",
    "precious_metals": "Precious Metals",
}

def load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def detect_impact(brick: str, regime: str, final_weight: float, raw_weight: float, confidence: float) -> str:
    if brick == "bonds":
        return "risk_reduction"
    if brick == "equities_defensive":
        return "stabilizer"
    if brick == "precious_metals":
        return "systemic_hedge"
    if brick in {"crypto", "equities_offensive"}:
        if raw_weight > final_weight + 1e-9:
            return "positive_but_capped"
        if confidence < 0.7:
            return "offensive_low_confidence"
        return "offensive_support"
    return "neutral"

def main():
    target = load_json(TARGET, {})
    audit = load_json(AUDIT, {})
    inputs = {}

    for fp in sorted(INPUTS.glob("*.json")):
        payload = load_json(fp, {})
        brick = payload.get("brick")
        if brick:
            inputs[brick] = payload

    raw_brick_weights = target.get("raw_brick_weights", {}) or {}
    final_brick_weights = target.get("final_brick_weights", {}) or {}
    brick_confidence = target.get("brick_confidence", {}) or {}
    brick_regimes = target.get("brick_regimes", {}) or {}
    cap_adjustments = target.get("cap_adjustments", {}) or {}
    caps_triggered = audit.get("portfolio_checks", {}).get("caps_triggered", []) or []

    decision_factors = []

    for brick in sorted(final_brick_weights.keys()):
        raw_weight = float(raw_brick_weights.get(brick, 0.0) or 0.0)
        final_weight = float(final_brick_weights.get(brick, 0.0) or 0.0)
        confidence = float(brick_confidence.get(brick, 0.0) or 0.0)
        regime = str(brick_regimes.get(brick, "unknown"))
        payload = inputs.get(brick, {})
        role = payload.get("portfolio_role", target.get("brick_roles", {}).get(brick))
        funding_pool = payload.get("funding_pool")
        cap_meta = cap_adjustments.get(target.get("brick_families", {}).get(brick, ""), {})
        capped = brick in {"crypto", "equities_offensive"} and "offensive" in caps_triggered

        decision_factors.append({
            "brick": brick,
            "label": BRICK_LABELS.get(brick, brick),
            "signal": regime,
            "confidence": confidence,
            "raw_weight": raw_weight,
            "final_weight": final_weight,
            "role": role,
            "funding_pool": funding_pool,
            "cap_applied": capped,
            "impact": detect_impact(brick, regime, final_weight, raw_weight, confidence),
        })

    portfolio_regime = target.get("portfolio_regime", "unknown")
    final_family_weights = target.get("final_family_weights", {}) or {}
    cash_buffer = float(target.get("cash_buffer", 0.0) or 0.0)

    reasons = []
    if portfolio_regime == "risk_off":
        reasons.append("Portfolio regime is risk_off.")
    if "offensive" in caps_triggered:
        reasons.append("Offensive family cap was triggered and reduced.")
    if final_family_weights.get("macro_defensive", 0) >= 0.2:
        reasons.append("Macro defensive sleeve remains materially allocated.")
    if final_family_weights.get("stabilization", 0) >= 0.2:
        reasons.append("Defensive stabilization sleeve remains active.")
    if final_family_weights.get("systemic_hedge", 0) > 0:
        reasons.append("Systemic hedge remains active.")
    if cash_buffer > 0:
        reasons.append(f"Cash buffer retained at {cash_buffer:.2f}.")

    result = {
        "status": "ok",
        "engine": "aggregator_explainability_v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "portfolio_regime": portfolio_regime,
        "decision_factors": decision_factors,
        "final_decision": {
            "regime": portfolio_regime,
            "caps_triggered": caps_triggered,
            "cash_buffer": cash_buffer,
            "family_mix": final_family_weights,
            "reason_summary": reasons,
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
