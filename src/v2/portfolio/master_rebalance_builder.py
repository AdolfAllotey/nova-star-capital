from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict


DATA = Path("/opt/nsc/data/preprod")
PORTFOLIO = DATA / "portfolio"

TARGET_PATH = PORTFOLIO / "portfolio_target.json"
STATE_PATH = PORTFOLIO / "state" / "portfolio_state.json"
POLICY_PATH = PORTFOLIO / "policy" / "allocation_policy.json"
EXECUTION_PLAN_PATH = DATA / "trading" / "execution_plan.json"
OFFENSIVE_EXECUTION_PLAN_PATH = DATA / "equities_offensive" / "execution" / "execution_plan.json"

REBALANCE_PATH = PORTFOLIO / "rebalance" / "rebalance_plan.json"
FUNDING_PATH = PORTFOLIO / "rebalance" / "funding_plan.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def main() -> int:
    target = load(TARGET_PATH, {})
    state = load(STATE_PATH, {})
    policy = load(POLICY_PATH, {})
    execution_plan = load(EXECUTION_PLAN_PATH, {})
    offensive_execution_plan = load(OFFENSIVE_EXECUTION_PLAN_PATH, {})

    execution_orders = execution_plan.get("orders", []) if isinstance(execution_plan, dict) else []
    if not isinstance(execution_orders, list):
        execution_orders = []

    offensive_orders = offensive_execution_plan.get("orders", []) if isinstance(offensive_execution_plan, dict) else []
    if not isinstance(offensive_orders, list):
        offensive_orders = []

    offensive_has_buy_orders = any(
        isinstance(o, dict) and str(o.get("side", "")).upper() == "BUY"
        for o in offensive_orders
    )
    offensive_has_only_sell_orders = bool(offensive_orders) and not offensive_has_buy_orders

    crypto_execution_orders = [
        o for o in execution_orders
        if isinstance(o, dict) and str(o.get("symbol", "")).lower().endswith("usdt")
    ]

    regime = target.get("portfolio_regime") or state.get("portfolio_regime") or "unknown"
    capital = f(
        state.get("capital_context", {}).get("deployable_capital_eur"),
        10000.0,
    )

    target_weights = target.get("final_brick_weights", {}) if isinstance(target, dict) else {}
    bricks_state = state.get("bricks", {}) if isinstance(state, dict) else {}
    inertia = policy.get("brick_inertia", {}) if isinstance(policy, dict) else {}

    actions = []
    funding_by_pool: Dict[str, Dict[str, Any]] = {
        "crypto_exchange_pool": {"pool": "crypto_exchange_pool", "net_required_eur": 0.0, "manual_transfer_required": False, "items": []},
        "ibkr_pool": {"pool": "ibkr_pool", "net_required_eur": 0.0, "manual_transfer_required": False, "items": []},
    }

    for brick, tw in sorted(target_weights.items()):
        bstate = bricks_state.get(brick, {}) if isinstance(bricks_state, dict) else {}
        target_weight = f(tw)
        current_weight = f(bstate.get("current_weight_estimate"), target_weight)
        delta_weight = round(target_weight - current_weight, 6)
        target_amount = round(target_weight * capital, 2)
        current_amount = round(current_weight * capital, 2)
        delta_amount = round(target_amount - current_amount, 2)

        funding_pool = bstate.get("funding_pool", "ibkr_pool")
        brick_inertia = inertia.get(brick, {}) if isinstance(inertia, dict) else {}
        threshold = f(brick_inertia.get("min_threshold_to_rebalance"), 0.03)
        max_change = f(brick_inertia.get("max_weight_change_per_cycle"), 0.03)

        abs_delta = abs(delta_weight)

        if brick == "crypto" and delta_weight > 0 and len(crypto_execution_orders) == 0:
            status = "deferred"
            priority = "low"
            reason = (
                f"delta_weight={delta_weight} above threshold={threshold}, "
                "but deferred because crypto execution_plan has zero valid orders"
            )
            proposed_delta_weight = 0.0
        elif abs_delta < threshold:
            status = "deferred"
            priority = "low"
            reason = f"delta_weight={delta_weight} below threshold={threshold}"
            proposed_delta_weight = 0.0
        else:
            status = "proposed"
            priority = "medium"
            proposed_delta_weight = max(-max_change, min(max_change, delta_weight))
            reason = f"delta_weight={delta_weight} above threshold={threshold}; capped by inertia={max_change}"

        if brick == "equities_offensive" and delta_weight > 0 and offensive_has_only_sell_orders:
            status = "deferred"
            priority = "low"
            proposed_delta_weight = 0.0
            reason = (
                f"delta_weight={delta_weight} above threshold={threshold}, "
                "but deferred because offensive execution_plan contains SELL-only take-profit orders"
            )

        proposed_delta_amount = round(proposed_delta_weight * capital, 2)

        action = {
            "brick": brick,
            "funding_pool": funding_pool,
            "target_weight": target_weight,
            "current_weight_estimate": current_weight,
            "delta_weight": delta_weight,
            "target_amount_eur": target_amount,
            "current_amount_estimate_eur": current_amount,
            "delta_amount_eur": delta_amount,
            "proposed_delta_weight": proposed_delta_weight,
            "proposed_delta_amount_eur": proposed_delta_amount,
            "status": status,
            "priority": priority,
            "reason": reason,
            "manual_approval_required": True,
            "execution_allowed": False
        }
        actions.append(action)

        if funding_pool in funding_by_pool and proposed_delta_amount != 0:
            funding_by_pool[funding_pool]["net_required_eur"] = round(
                funding_by_pool[funding_pool]["net_required_eur"] + proposed_delta_amount,
                2,
            )
            funding_by_pool[funding_pool]["items"].append(action)

    funding_plan = {
        "status": "ok",
        "engine": "master_funding_plan_v1",
        "env": "PREPROD",
        "generated_at": now(),
        "portfolio_regime": regime,
        "rule": "No automatic inter-universe transfer. Crypto ↔ IBKR funding requires explicit manual approval.",
        "execution_allowed": False,
        "manual_approval_required": True,
        "funding_pools": list(funding_by_pool.values()),
        "inter_universe_transfer": {
            "crypto_exchange_pool_to_ibkr_pool": "manual_only",
            "ibkr_pool_to_crypto_exchange_pool": "manual_only",
            "automatic_transfer_allowed": False
        }
    }

    rebalance_plan = {
        "status": "ok",
        "engine": "master_rebalance_plan_v1",
        "env": "PREPROD",
        "generated_at": now(),
        "portfolio_regime": regime,
        "source_of_truth": True,
        "execution_allowed": False,
        "manual_approval_required": True,
        "manual_funding_required": True,
        "automatic_inter_universe_transfer": False,
        "policy_source": str(POLICY_PATH),
        "target_source": str(TARGET_PATH),
        "state_source": str(STATE_PATH),
        "actions": actions,
        "summary": {
            "actions_total": len(actions),
            "actions_proposed": sum(1 for a in actions if a["status"] == "proposed"),
            "actions_deferred": sum(1 for a in actions if a["status"] == "deferred"),
            "capital_eur": capital
        },
        "funding_plan_path": str(FUNDING_PATH)
    }

    save(REBALANCE_PATH, rebalance_plan)
    save(PORTFOLIO / "rebalance_plan.json", rebalance_plan)

    
    for pool in funding_plan.get("funding_pools", []):
        net_required = float(pool.get("net_required_eur", 0.0) or 0.0)
        pool["manual_transfer_required"] = round(net_required, 2) != 0.0

    save(FUNDING_PATH, funding_plan)
    save(PORTFOLIO / "funding_plan.json", funding_plan)

    print(json.dumps({
        "rebalance_plan": str(REBALANCE_PATH),
        "funding_plan": str(FUNDING_PATH),
        "actions_total": len(actions),
        "actions_proposed": rebalance_plan["summary"]["actions_proposed"],
        "execution_allowed": False
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
