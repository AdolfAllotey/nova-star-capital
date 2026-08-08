#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime, UTC

PORTFOLIO_DIR = Path("/opt/nsc/app/src/v2/data/portfolio")
TARGET_PATH = PORTFOLIO_DIR / "portfolio_target.json"
AUDIT_PATH = PORTFOLIO_DIR / "aggregator_audit.json"
STATE_PATH = Path("/opt/nsc/data/preprod/portfolio/state/portfolio_state.json")
OUTPUT_PATH = PORTFOLIO_DIR / "aggregator_anomalies.json"

DRIFT_THRESHOLD = 0.05

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
    state = load_json(STATE_PATH, {})

    anomalies = []
    warnings = []

    final_weights = target.get("final_brick_weights", {}) or {}
    cash_buffer = float(target.get("cash_buffer", 0.0) or 0.0)
    total_final = float(target.get("total_final_weight", 0.0) or 0.0)
    bricks = state.get("bricks", {}) or {}

    # 1. Check total consistency
    if abs((total_final + cash_buffer) - 1.0) > 0.05:
        anomalies.append({
            "type": "cash_consistency_error",
            "expected_sum": 1.0,
            "observed_sum": round(total_final + cash_buffer, 6),
        })

    # 2. Check target vs current estimate
    for brick, target_weight in final_weights.items():
        brick_state = bricks.get(brick, {}) if isinstance(bricks, dict) else {}
        current_est = float(brick_state.get("current_weight_estimate", 0.0) or 0.0)
        drift = round(current_est - float(target_weight), 6)

        if abs(drift) >= DRIFT_THRESHOLD:
            warnings.append({
                "type": "weight_drift",
                "brick": brick,
                "target_weight": round(float(target_weight), 6),
                "current_weight_estimate": round(current_est, 6),
                "drift": drift,
            })

    # 3. Caps triggered
    caps = audit.get("portfolio_checks", {}).get("caps_triggered", []) or []
    for cap in caps:
        warnings.append({
            "type": "family_cap_triggered",
            "family": cap,
        })

    # 4. Pass-through warnings/anomalies from audit
    for w in audit.get("warnings", []) or []:
        warnings.append({
            "type": "audit_warning",
            "message": w,
        })

    for a in audit.get("anomalies", []) or []:
        anomalies.append({
            "type": "audit_anomaly",
            "message": a,
        })

    result = {
        "status": "ok" if not anomalies else "warning",
        "engine": "aggregator_anomalies_v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "thresholds": {
            "weight_drift_warning": DRIFT_THRESHOLD
        },
        "warnings": warnings,
        "anomalies": anomalies,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
