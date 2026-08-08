import json
import os
from datetime import datetime
from pathlib import Path


DEFAULT_DATA_DIR = "/opt/nsc/data/preprod"
DATA_DIR = Path(os.getenv("NSC_DATA_DIR", DEFAULT_DATA_DIR))
PORTFOLIO_DIR = DATA_DIR / "portfolio"

REBALANCE_PATH = PORTFOLIO_DIR / "rebalance" / "rebalance_plan.json"
POLICY_PATH = PORTFOLIO_DIR / "policy" / "allocation_policy.json"
OUTPUT_PATH = PORTFOLIO_DIR / "rebalance" / "funding_plan.json"


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(data, path: Path):
    data["timestamp"] = datetime.utcnow().isoformat()
    ensure_parent(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_funding_plan_builder():
    rebalance = load_json(REBALANCE_PATH)
    policy = load_json(POLICY_PATH)

    inter_pool_rules = policy.get("inter_pool_rules", {}) or {}
    all_actions = rebalance.get("actions", []) or []
    approved_actions = [a for a in all_actions if a.get("status") == "approved"]

    pool_actions = {}
    net_delta_by_pool = {}
    net_reduce_by_pool = {}
    net_increase_by_pool = {}

    for action in approved_actions:
        pool = action.get("funding_pool", "unknown")
        delta = float(action.get("approved_delta", 0.0) or 0.0)

        pool_actions.setdefault(pool, []).append(action)
        net_delta_by_pool[pool] = round(net_delta_by_pool.get(pool, 0.0) + delta, 6)

        if delta < 0:
            net_reduce_by_pool[pool] = round(net_reduce_by_pool.get(pool, 0.0) + abs(delta), 6)
        elif delta > 0:
            net_increase_by_pool[pool] = round(net_increase_by_pool.get(pool, 0.0) + delta, 6)

    intra_pool_actions = {pool: actions for pool, actions in pool_actions.items()}

    intra_pool_match_possible = {}
    for pool in set(list(net_reduce_by_pool.keys()) + list(net_increase_by_pool.keys())):
        reduce_amt = float(net_reduce_by_pool.get(pool, 0.0) or 0.0)
        increase_amt = float(net_increase_by_pool.get(pool, 0.0) or 0.0)
        intra_pool_match_possible[pool] = reduce_amt > 0 and increase_amt > 0

    inter_pool_candidates = []
    manual_transfer_tickets = []
    manual_transfer_candidates = []

    pools_with_positive_need = [pool for pool, delta in net_increase_by_pool.items() if delta > 0]
    pools_with_negative_need = [pool for pool, delta in net_reduce_by_pool.items() if delta > 0]

    if pools_with_positive_need and pools_with_negative_need:
        for source_pool in pools_with_negative_need:
            for destination_pool in pools_with_positive_need:
                if source_pool == destination_pool:
                    continue

                candidate = {
                    "from_pool": source_pool,
                    "to_pool": destination_pool,
                    "available_reduction": round(float(net_reduce_by_pool.get(source_pool, 0.0) or 0.0), 6),
                    "required_increase": round(float(net_increase_by_pool.get(destination_pool, 0.0) or 0.0), 6),
                    "auto_transfer_allowed": bool(inter_pool_rules.get("auto_transfer_allowed", False)),
                    "manual_transfer_required": bool(inter_pool_rules.get("manual_transfer_required", True)),
                    "reason": "Cross-pool rebalance detected between independent funding pools."
                }
                inter_pool_candidates.append(candidate)

                if candidate["manual_transfer_required"]:
                    manual_transfer_candidates.append(candidate)
                    manual_transfer_tickets.append({
                        "ticket_type": "manual_inter_pool_transfer",
                        "from_pool": source_pool,
                        "to_pool": destination_pool,
                        "status": "pending_manual_execution",
                        "amount_hint": round(min(candidate["available_reduction"], candidate["required_increase"]), 6),
                        "reason": "NSC policy forbids automatic transfer between funding pools."
                    })

    funding_plan = {
        "status": "ok",
        "engine": "funding_plan_builder_v2",
        "data_dir": str(DATA_DIR),
        "auto_transfer_allowed": inter_pool_rules.get("auto_transfer_allowed", False),
        "manual_transfer_required": inter_pool_rules.get("manual_transfer_required", True),
        "requires_manual_transfer_between_pools": len(manual_transfer_tickets) > 0,
        "approved_actions_count": len(approved_actions),
        "net_delta_by_pool": net_delta_by_pool,
        "net_reduce_by_pool": net_reduce_by_pool,
        "net_increase_by_pool": net_increase_by_pool,
        "intra_pool_match_possible": intra_pool_match_possible,
        "intra_pool_actions": intra_pool_actions,
        "inter_pool_candidates": inter_pool_candidates,
        "manual_transfer_candidates": manual_transfer_candidates,
        "manual_transfer_tickets": manual_transfer_tickets,
        "notes": [
            "V2 distinguishes net reductions and net increases by pool.",
            "V2 prepares future pool matching and manual transfer orchestration.",
            "Inter-pool funding remains manual-only by NSC policy."
        ]
    }

    save_json(funding_plan, OUTPUT_PATH)
    return funding_plan


if __name__ == "__main__":
    result = run_funding_plan_builder()
    print(json.dumps(result, indent=2))
