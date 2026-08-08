from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


APP_DATA = Path("/opt/nsc/app/src/v2/data")
PREPROD_DATA = Path("/opt/nsc/data/preprod")

REBALANCE_PATH = APP_DATA / "portfolio/rebalance/rebalance_plan.json"
EXEC_PLAN_PATH = PREPROD_DATA / "trading/execution_plan.json"
OUTPUT_PATH = APP_DATA / "portfolio/rebalance/execution_alignment_audit.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": str(exc), "__path__": str(path)}


def main() -> None:
    rebalance = load_json(REBALANCE_PATH)
    execution = load_json(EXEC_PLAN_PATH)

    warnings = []
    blockers = []

    approved_reductions = [
        a for a in rebalance.get("actions", [])
        if a.get("status") == "approved"
        and a.get("action") == "reduce"
        and float(a.get("approved_delta") or 0) < 0
    ]

    orders = execution.get("orders", []) if isinstance(execution.get("orders"), list) else []

    order_symbols = [str(o.get("symbol", "")).lower() for o in orders if isinstance(o, dict)]
    order_sides = [str(o.get("side", "")).lower() for o in orders if isinstance(o, dict)]

    if approved_reductions and orders:
      warnings.append(
          "Execution plan contains orders while rebalance plan has approved reduction intents. "
          "This is acceptable in audit/preprod only if execution policy remains SIMULATED_ONLY."
      )

    gov = execution.get("governance", {}) if isinstance(execution.get("governance"), dict) else {}
    action_policy = gov.get("action_policy")
    hard_block = bool(gov.get("hard_block"))

    if action_policy != "SIMULATED_ONLY":
        blockers.append(f"execution action_policy is {action_policy}, expected SIMULATED_ONLY in preprod alignment audit")

    if hard_block and orders:
        blockers.append("hard_block=true but execution plan still contains orders")

    output = {
        "status": "ok" if not blockers else "blocked",
        "engine": "execution_alignment_audit_preprod_v0",
        "mode": "PREPROD_AUDIT_ONLY",
        "timestamp": now_iso(),
        "execution_allowed": False,
        "writes_execution_plan": False,
        "rebalance": {
            "portfolio_regime": rebalance.get("portfolio_regime"),
            "policy_mode": rebalance.get("policy_mode"),
            "approved_reduction_count": len(approved_reductions),
            "approved_reductions": [
                {
                    "brick": a.get("brick"),
                    "approved_delta": a.get("approved_delta"),
                    "funding_pool": a.get("funding_pool"),
                    "reason": a.get("reason"),
                }
                for a in approved_reductions
            ],
        },
        "execution_plan": {
            "path": str(EXEC_PLAN_PATH),
            "status": execution.get("status"),
            "env": execution.get("env"),
            "action_policy": action_policy,
            "hard_block": hard_block,
            "orders_count": len(orders),
            "order_sides": sorted(set(order_sides)),
            "order_symbols": order_symbols[:20],
        },
        "warnings": warnings,
        "blockers": blockers,
        "recommendation": (
            "Keep execution independent but blocked/simulated until rebalance bridge is explicitly governed. "
            "Next step: add read-only rebalance awareness to Control Room."
        ),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
