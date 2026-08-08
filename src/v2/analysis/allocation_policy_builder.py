#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime, UTC

PORTFOLIO_DIR = Path("/opt/nsc/app/src/v2/data/portfolio")
TARGET_PATH = PORTFOLIO_DIR / "portfolio_target.json"
AUDIT_PATH = PORTFOLIO_DIR / "aggregator_audit.json"
EXPLAIN_PATH = PORTFOLIO_DIR / "aggregator_explainability.json"
OUTPUT_PATH = PORTFOLIO_DIR / "allocation_policy.json"

DEFAULT_CAPS = {
    "offensive": 0.30,
    "stabilization": 0.25,
    "macro_defensive": 0.40,
    "systemic_hedge": 0.20,
}

def load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def main():
    target = load_json(TARGET_PATH, {})
    audit = load_json(AUDIT_PATH, {})
    explain = load_json(EXPLAIN_PATH, {})

    regime = target.get("portfolio_regime", "unknown")
    family_caps = target.get("family_caps", DEFAULT_CAPS) or DEFAULT_CAPS
    final_family_weights = target.get("final_family_weights", {}) or {}
    cash_buffer = float(target.get("cash_buffer", 0.0) or 0.0)
    caps_triggered = audit.get("portfolio_checks", {}).get("caps_triggered", []) or []
    warnings = audit.get("warnings", []) or []
    anomalies = audit.get("anomalies", []) or []
    reason_summary = explain.get("final_decision", {}).get("reason_summary", []) or []

    rules = {
        "allocation_mode": "dynamic_under_constraints",
        "cash_policy": "excess_after_caps_goes_to_cash",
        "redistribution_policy": "no_automatic_redistribution",
        "capital_preservation_bias": regime == "risk_off",
        "family_caps": family_caps,
        "cash_buffer_target": cash_buffer,
    }

    policy = {
        "status": "ok" if not anomalies else "warning",
        "engine": "allocation_policy_builder_v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "regime": regime,
        "rules": rules,
        "caps_triggered": caps_triggered,
        "family_mix": final_family_weights,
        "warnings": warnings,
        "anomalies": anomalies,
        "reason_summary": reason_summary,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    print(json.dumps(policy, indent=2))

if __name__ == "__main__":
    main()
