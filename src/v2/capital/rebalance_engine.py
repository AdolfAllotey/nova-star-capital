from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


PORTFOLIO_STATE_PATH = Path("data/capital/portfolio_state_normalized.json")
GOVERNOR_PATH = Path("data/capital/capital_governor_decision.json")
OUTPUT_PATH = Path("data/capital/rebalance_plan.json")


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


def classify_action(delta_eur: float, threshold_eur: float) -> str:
    if delta_eur > threshold_eur:
        return "increase"
    if delta_eur < -threshold_eur:
        return "reduce"
    return "hold"


def build_actions(
    portfolio_state: Dict[str, Any],
    governor: Dict[str, Any],
    min_action_eur: float = 50.0
) -> List[Dict[str, Any]]:
    nav = safe_float(portfolio_state.get("nav_eur", 0.0))
    target_amounts = portfolio_state.get("target_amounts_eur", {}) or {}
    current_values = portfolio_state.get("current_values_eur", {}) or {}

    actions: List[Dict[str, Any]] = []

    all_keys = sorted(set(target_amounts.keys()) | set(current_values.keys()))

    mapping_notes = {
        "crypto": "portfolio target brick",
        "equities_offensive": "portfolio target brick",
        "equities_defensive": "portfolio target brick",
        "bonds": "portfolio target brick",
        "precious_metals": "portfolio target brick",
        "crypto_trading": "runtime pocket",
        "crypto_lt": "long term pocket",
        "equities_lt": "long term pocket",
        "cash": "reserve",
        "tax_reserve": "reserve",
        "bfr_reserve": "reserve",
        "security_reserve": "reserve"
    }

    protected_no_reduce = {"crypto_lt", "equities_lt", "tax_reserve", "security_reserve"}
    funding_sources = {"cash", "bfr_reserve"}

    for key in all_keys:
        target = safe_float(target_amounts.get(key, 0.0))
        current = safe_float(current_values.get(key, 0.0))
        delta = round(target - current, 2)
        action = classify_action(delta, min_action_eur)

        reason = "Below rebalance threshold"
        status = "deferred"

        if action != "hold":
            reason = "Target/state drift above threshold"
            status = "proposed"

        if action == "reduce" and key in funding_sources:
            status = "deferred"
            reason = "Funding source bucket; not reduced by rebalance engine"

        if action == "reduce" and key in protected_no_reduce:
            status = "deferred"
            reason = "Protected patrimonial/reserve bucket; reduction excluded outside survival"

        actions.append({
            "bucket": key,
            "action": action,
            "status": status,
            "target_eur": round(target, 2),
            "current_eur": round(current, 2),
            "delta_eur": delta,
            "delta_weight": round(delta / nav, 6) if nav > 0 else 0.0,
            "reason": reason,
            "note": mapping_notes.get(key, "unmapped")
        })

    priority = {
        "reduce": 0,
        "increase": 1,
        "hold": 2
    }

    actions.sort(key=lambda x: (priority.get(x["action"], 9), -abs(safe_float(x["delta_eur"]))))
    return actions


def run() -> Dict[str, Any]:
    portfolio_state = read_json(PORTFOLIO_STATE_PATH, default={}) or {}
    governor = read_json(GOVERNOR_PATH, default={}) or {}

    actions = build_actions(portfolio_state, governor)

    proposed = [a for a in actions if a.get("status") == "proposed"]

    plan = {
        "status": "proposed" if proposed else "idle",
        "engine": "rebalance_engine_v3",
        "mode": governor.get("mode", "UNKNOWN"),
        "nav_eur": portfolio_state.get("nav_eur", 0.0),
        "min_action_eur": 50.0,
        "actions": actions,
        "kpis": {
            "actions_total": len(actions),
            "actions_proposed": len(proposed),
            "increase_count": sum(1 for a in proposed if a.get("action") == "increase"),
            "reduce_count": sum(1 for a in proposed if a.get("action") == "reduce")
        },
        "guardrails": {
            "automatic_execution": False,
            "requires_governance_approval": True,
            "inter_broker_transfer_auto_allowed": False
        },
        "notes": [
            "V3 compares normalized target/state and excludes funding-source and protected LT reductions.",
            "Plan is advisory only: no execution, no transfer.",
            "Funding engine must validate broker constraints before any transfer."
        ]
    }

    write_json(OUTPUT_PATH, plan)
    return plan


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
