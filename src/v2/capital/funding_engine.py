from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


REBALANCE_PLAN_PATH = Path("data/capital/rebalance_plan.json")
PORTFOLIO_STATE_PATH = Path("data/capital/portfolio_state.json")
GOVERNOR_PATH = Path("data/capital/capital_governor_decision.json")
FUNDING_POLICY_PATH = Path("data/capital/policies/funding_policy.json")
CAPITAL_CONTEXT_PATH = Path("data/capital/config/capital_context.json")
OUTPUT_PATH = Path("data/capital/funding_plan.json")


BUCKET_TO_POOL = {
    "crypto": "crypto_exchange_pool",
    "crypto_trading": "crypto_exchange_pool",
    "crypto_lt": "crypto_exchange_pool",

    "equities_offensive": "ibkr_pool",
    "equities_defensive": "ibkr_pool",
    "equities_lt": "ibkr_pool",
    "bonds": "ibkr_pool",
    "precious_metals": "ibkr_pool",
    "gold": "ibkr_pool",
    "options": "ibkr_pool",
    "options_us": "ibkr_pool",

    "cash": "treasury_pool",
    "tax_reserve": "treasury_pool",
    "bfr_reserve": "treasury_pool",
    "security_reserve": "treasury_pool"
}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def is_protected(bucket: str, policy: Dict[str, Any]) -> Dict[str, Any]:
    protected = policy.get("protected_buckets", {}) if isinstance(policy, dict) else {}
    rule = protected.get(bucket, {})
    if isinstance(rule, dict):
        return rule
    return {}


def pool_for(bucket: str) -> str:
    return BUCKET_TO_POOL.get(bucket, "unknown_pool")


def build_transfer_instruction(
    *,
    action: Dict[str, Any],
    policy: Dict[str, Any],
    governor: Dict[str, Any]
) -> Dict[str, Any]:
    bucket = str(action.get("bucket", "unknown"))
    action_type = str(action.get("action", "hold"))
    amount = abs(safe_float(action.get("delta_eur", 0.0)))
    pool = pool_for(bucket)
    mode = str(governor.get("mode", "UNKNOWN"))

    protected_rule = is_protected(bucket, policy)

    base = {
        "bucket": bucket,
        "action": action_type,
        "amount_eur": round(amount, 2),
        "target_pool": pool,
        "status": "proposed",
        "mode": mode,
        "automatic_execution": False,
        "requires_governance_approval": True,
        "source_rebalance_reason": action.get("reason"),
        "notes": []
    }

    if action_type == "hold" or amount <= 0:
        base["status"] = "ignored"
        base["notes"].append("No funding action required.")
        return base

    if action_type == "reduce":
        if protected_rule and protected_rule.get("can_reduce") is False and mode != "SURVIVAL":
            base["status"] = "blocked"
            base["block_reason"] = protected_rule.get("reason", "protected bucket cannot be reduced")
            base["notes"].append("Protected bucket reduction blocked outside SURVIVAL mode.")
            return base

        base["funding_type"] = "release_capital"
        base["from_bucket"] = bucket
        base["to_bucket"] = "cash"
        base["route"] = [pool, "treasury_pool"] if pool != "treasury_pool" else ["treasury_pool"]
        base["manual_transfer_required"] = pool != "treasury_pool"
        return base

    if action_type == "increase":
        base["funding_type"] = "allocate_capital"
        base["from_bucket"] = "cash"
        base["to_bucket"] = bucket

        source_pool = pool_for("cash")
        target_pool = pool

        base["route"] = [source_pool, target_pool] if source_pool != target_pool else [target_pool]
        base["manual_transfer_required"] = source_pool != target_pool

        if source_pool != target_pool:
            base["status"] = "manual_review_required"
            base["notes"].append("Inter-pool transfer requires manual/governed approval.")

        return base

    base["status"] = "ignored"
    base["notes"].append("Unsupported action type.")
    return base


def run() -> Dict[str, Any]:
    rebalance = read_json(REBALANCE_PLAN_PATH, default={}) or {}
    portfolio_state = read_json(PORTFOLIO_STATE_PATH, default={}) or {}
    governor = read_json(GOVERNOR_PATH, default={}) or {}
    policy = read_json(FUNDING_POLICY_PATH, default={}) or {}
    context = read_json(CAPITAL_CONTEXT_PATH, default={}) or {}

    actions = rebalance.get("actions", []) if isinstance(rebalance.get("actions"), list) else []

    transfers: List[Dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("status") != "proposed":
            continue
        transfers.append(build_transfer_instruction(
            action=action,
            policy=policy,
            governor=governor
        ))

    plan = {
        "status": "proposed" if transfers else "idle",
        "engine": "funding_engine_v2",
        "currency": "EUR",
        "capital_context": context,
        "mode": governor.get("mode", "UNKNOWN"),
        "nav_eur": portfolio_state.get("nav_eur", 0.0),
        "transfers": transfers,
        "kpis": {
            "transfers_total": len(transfers),
            "manual_review_required": sum(1 for t in transfers if t.get("status") == "manual_review_required"),
            "blocked": sum(1 for t in transfers if t.get("status") == "blocked"),
            "proposed": sum(1 for t in transfers if t.get("status") == "proposed")
        },
        "guardrails": {
            "automatic_transfers_allowed": bool(context.get("real_broker_funding_enabled", False)),
            "requires_governance_approval": True,
            "inter_broker_transfer_auto_allowed": False,
            "lt_reduction_blocked_outside_survival": True,
            "tax_and_security_reserve_protected": True
        },
        "policy_source": str(FUNDING_POLICY_PATH),
        "notes": [
            "Funding Engine V2 converts rebalance proposals into governed funding instructions.",
            "No broker transfer is executed by this engine.",
            "Inter-broker and inter-pool transfers require manual/governed approval."
        ]
    }

    write_json(OUTPUT_PATH, plan)
    return plan


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
