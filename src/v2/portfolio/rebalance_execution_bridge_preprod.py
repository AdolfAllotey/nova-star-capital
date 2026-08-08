from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("/opt/nsc/app/src/v2/data")
REBALANCE_PATH = DATA_DIR / "portfolio/rebalance/rebalance_plan.json"
OUTPUT_PATH = DATA_DIR / "portfolio/rebalance/rebalance_execution_bridge_audit.json"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error", "error": str(exc), "path": str(path)}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    plan = load_json(REBALANCE_PATH)
    actions = plan.get("actions", []) if isinstance(plan, dict) else []

    proposals = []
    warnings = []

    for a in actions:
        if a.get("status") != "approved":
            continue

        approved_delta = float(a.get("approved_delta") or 0)
        if approved_delta == 0:
            continue

        proposal = {
            "brick": a.get("brick"),
            "source_action": a.get("action"),
            "approved_delta": approved_delta,
            "funding_pool": a.get("funding_pool"),
            "manual_transfer_required": bool(a.get("manual_transfer_required")),
            "execution_intent": "REDUCE_EXPOSURE" if approved_delta < 0 else "INCREASE_EXPOSURE",
            "execution_allowed": False,
            "execution_mode": "AUDIT_ONLY",
            "reason": a.get("reason"),
            "rationale": a.get("rationale", []),
        }

        if approved_delta > 0 and proposal["manual_transfer_required"]:
            proposal["blocked_by"] = ["manual_transfer_required"]
        else:
            proposal["blocked_by"] = ["shadow_audit_only"]

        proposals.append(proposal)

    if not proposals:
        warnings.append("No approved rebalance actions requiring execution bridge proposal.")

    output = {
        "status": "ok",
        "engine": "rebalance_execution_bridge_preprod_v0",
        "mode": "PREPROD_SHADOW_AUDIT_ONLY",
        "timestamp": now_iso(),
        "source_rebalance_plan": str(REBALANCE_PATH),
        "portfolio_regime": plan.get("portfolio_regime"),
        "policy_mode": plan.get("policy_mode"),
        "execution_allowed": False,
        "writes_execution_plan": False,
        "proposal_count": len(proposals),
        "proposals": proposals,
        "warnings": warnings,
        "notes": [
            "Audit-only bridge. Does not write execution_plan.json.",
            "Approved rebalance actions are translated into execution intents only.",
            "Execution must remain governed by governance/risk/execution_engine_pro."
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
