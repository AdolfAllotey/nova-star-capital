#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime, UTC

INPUT_DIR = Path("src/v2/data/portfolio/inputs")
TARGET_FILE = Path("src/v2/data/portfolio/portfolio_target.json")
OUTPUT_FILE = Path("src/v2/data/portfolio/aggregator_audit.json")

EXPECTED_BRICKS = {
    "bonds",
    "crypto",
    "equities_defensive",
    "equities_offensive",
    "precious_metals"
}


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def check_allocation_sum(allocation):
    if not isinstance(allocation, dict) or not allocation:
        return False, 0.0
    s = sum(float(v or 0) for v in allocation.values())
    return abs(s - 1.0) < 0.05, s


def main():
    inputs = list(INPUT_DIR.glob("*.json"))

    warnings = []
    anomalies = []
    bricks_found = set()

    # --- INPUT CHECK ---
    for f in inputs:
        data = load_json(f)
        if not data:
            anomalies.append(f"{f.name} unreadable")
            continue

        brick = data.get("brick")
        bricks_found.add(brick)

        if not brick:
            anomalies.append(f"{f.name}: missing brick")

        if not isinstance(data.get("enabled"), bool):
            warnings.append(f"{brick}: enabled missing or not bool")

        tw = data.get("target_weight") or data.get("target_exposure")
        if not isinstance(tw, (int, float)):
            anomalies.append(f"{brick}: invalid target_weight")
        elif tw < 0 or tw > 1:
            anomalies.append(f"{brick}: target_weight out of range")

        conf = data.get("confidence")
        if not isinstance(conf, (int, float)):
            warnings.append(f"{brick}: missing confidence")
        elif conf < 0 or conf > 1:
            anomalies.append(f"{brick}: confidence out of range")

        alloc_ok, alloc_sum = check_allocation_sum(data.get("allocation"))
        if not alloc_ok:
            anomalies.append(f"{brick}: allocation sum = {alloc_sum:.2f}")

        if "timestamp" not in data:
            warnings.append(f"{brick}: missing timestamp")

        if "funding_pool" not in data:
            warnings.append(f"{brick}: missing funding_pool")

        # Special case crypto
        if brick == "crypto":
            warnings.append("crypto allocation is strategy-based")

    # Missing bricks
    missing = EXPECTED_BRICKS - bricks_found
    if missing:
        anomalies.append(f"missing bricks: {list(missing)}")

    # --- TARGET CHECK ---
    target = load_json(TARGET_FILE)

    portfolio_checks = {}

    if target:
        total_final = float(target.get("total_final_weight", 0))
        cash = float(target.get("cash_buffer", 0))

        portfolio_checks = {
            "portfolio_regime": target.get("portfolio_regime"),
            "total_final_weight": total_final,
            "cash_buffer": cash,
            "sum_with_cash": total_final + cash,
            "caps_triggered": [
                k for k, v in target.get("cap_adjustments", {}).items()
                if v.get("applied")
            ]
        }

        if abs((total_final + cash) - 1.0) > 0.05:
            anomalies.append("total_final_weight + cash_buffer != 1")

    else:
        anomalies.append("portfolio_target.json missing")

    # --- FINAL OUTPUT ---
    result = {
        "status": "ok" if not anomalies else "warning",
        "engine": "aggregator_audit_v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "inputs_found": len(inputs),
        "inputs_expected": len(EXPECTED_BRICKS),
        "warnings": warnings,
        "anomalies": anomalies,
        "portfolio_checks": portfolio_checks
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
