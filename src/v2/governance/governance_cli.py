#!/usr/bin/env python3
import json
import argparse
from pathlib import Path

from src.v2.governance.governance_loader import load_governance
from src.v2.governance.governance_enforcer import enforce_governance_on_plan

def read_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="Path to execution_plan.json")
    ap.add_argument("--notional", type=float, default=0.0, help="Optional estimated notional USD")
    ap.add_argument("--correlation-active", action="store_true", help="Simulate correlation gate active (soft veto)")
    args = ap.parse_args()

    g = load_governance()
    plan = read_json(Path(args.plan))

    corr = {"active": True} if args.correlation_active else None
    allowed, vetos, plan_out = enforce_governance_on_plan(
        g, plan, estimated_notional_usd=args.notional if args.notional > 0 else None, correlation_gate_state=corr
    )

    print("allowed:", allowed)
    print("vetos:", vetos)
    print("plan.validations:", plan_out.get("validations"))

if __name__ == "__main__":
    main()
