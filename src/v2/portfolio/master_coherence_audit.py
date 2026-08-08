from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List


DATA = Path("/opt/nsc/data/preprod")
OUT = DATA / "portfolio" / "audit" / "master_coherence_audit.json"

PATHS = {
    "portfolio_target": DATA / "portfolio" / "portfolio_target.json",
    "portfolio_state": DATA / "portfolio" / "state" / "portfolio_state.json",
    "allocation_policy": DATA / "portfolio" / "policy" / "allocation_policy.json",
    "rebalance_plan": DATA / "portfolio" / "rebalance" / "rebalance_plan.json",
    "funding_plan": DATA / "portfolio" / "rebalance" / "funding_plan.json",
    "governance": DATA / "analysis" / "governance_engine_pro.json",
}


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


def keys(d: Any) -> List[str]:
    if isinstance(d, dict):
        return list(d.keys())
    return []


def main() -> None:
    docs = {name: load(path, {}) for name, path in PATHS.items()}

    warnings: List[str] = []
    errors: List[str] = []

    missing = [name for name, path in PATHS.items() if not path.exists()]
    for name in missing:
        errors.append(f"missing artifact: {name} -> {PATHS[name]}")

    target = docs["portfolio_target"]
    state = docs["portfolio_state"]
    policy = docs["allocation_policy"]
    rebalance = docs["rebalance_plan"]
    funding = docs["funding_plan"]
    governance = docs["governance"]

    target_regime = target.get("portfolio_regime")
    state_regime = state.get("portfolio_regime")
    rebalance_regime = rebalance.get("portfolio_regime")
    funding_regime = funding.get("portfolio_regime")

    for name, regime in {
        "portfolio_state": state_regime,
        "rebalance_plan": rebalance_regime,
        "funding_plan": funding_regime,
    }.items():
        if regime != target_regime:
            warnings.append(f"regime mismatch: {name}={regime} vs portfolio_target={target_regime}")

    target_weights = target.get("final_brick_weights", {}) if isinstance(target, dict) else {}
    state_bricks = state.get("bricks", {}) if isinstance(state, dict) else {}
    rebalance_actions = rebalance.get("actions", []) if isinstance(rebalance, dict) else []

    target_bricks = set(target_weights.keys()) if isinstance(target_weights, dict) else set()
    state_brick_keys_raw = set(state_bricks.keys()) if isinstance(state_bricks, dict) else set()

    # Observation-only bricks can exist in portfolio_state without being
    # active allocation targets. They must not create master coherence warnings.
    observation_state_bricks = {
        brick
        for brick, payload in (
            state_bricks.items()
            if isinstance(state_bricks, dict)
            else []
        )
        if (
            isinstance(payload, dict)
            and float(
                payload.get("target_weight_snapshot") or 0.0
            ) == 0.0
            and (
                payload.get("governed_target") is False
                or payload.get("status") in {
                    "shadow_active",
                    "policy_excluded_observation",
                    "ungoverned_observation",
                }
                or str(
                    payload.get("state_origin") or ""
                ).startswith("lt_passive")
            )
        )
    }

    state_brick_keys = (
        state_brick_keys_raw
        - observation_state_bricks
    )
    rebalance_bricks = {a.get("brick") for a in rebalance_actions if isinstance(a, dict)}

    if target_bricks != state_brick_keys:
        warnings.append(f"target/state bricks mismatch: target={sorted(target_bricks)} state={sorted(state_brick_keys)}")

    missing_in_rebalance = sorted(target_bricks - rebalance_bricks)
    if missing_in_rebalance:
        warnings.append(f"bricks missing in rebalance_plan: {missing_in_rebalance}")

    total_weight = round(sum(float(v or 0) for v in target_weights.values()), 6) if isinstance(target_weights, dict) else 0.0
    cash_buffer = round(float(target.get("cash_buffer", 0) or 0), 6) if isinstance(target, dict) else 0.0
    if abs((total_weight + cash_buffer) - 1.0) > 0.0005:
        warnings.append(f"weights + cash_buffer != 1.0: weights={total_weight}, cash={cash_buffer}")

    if policy.get("source_of_truth") is not True:
        errors.append("allocation_policy.source_of_truth is not true")

    if rebalance.get("execution_allowed") is not False:
        errors.append("rebalance_plan.execution_allowed should remain false in PREPROD master layer")

    if funding.get("execution_allowed") is not False:
        errors.append("funding_plan.execution_allowed should remain false in PREPROD master layer")

    if funding.get("inter_universe_transfer", {}).get("automatic_transfer_allowed") is not False:
        errors.append("funding_plan automatic inter-universe transfer must be false")

    gov_hard_block = bool(governance.get("hard_block", False))
    gov_action_policy = governance.get("action_policy")

    result = {
        "status": "ok" if not errors else "error",
        "engine": "master_coherence_audit_v1_1",
        "generated_at": now(),
        "env": "PREPROD",
        "summary": {
            "missing_artifacts": missing,
            "errors_count": len(errors),
            "warnings_count": len(warnings),
            "target_bricks_count": len(target_bricks),
            "state_bricks_count": len(state_brick_keys),
            "observation_state_bricks_ignored_count": len(observation_state_bricks),
            "rebalance_actions_count": len(rebalance_actions),
            "target_total_weight": total_weight,
            "cash_buffer": cash_buffer,
            "total_with_cash": round(total_weight + cash_buffer, 6),
            "governance_hard_block": gov_hard_block,
            "governance_action_policy": gov_action_policy,
        },
        "checks": {
            "paths": {name: str(path) for name, path in PATHS.items()},
            "target_bricks": sorted(target_bricks),
            "state_bricks": sorted(state_brick_keys),
            "state_bricks_raw": sorted(state_brick_keys_raw),
            "observation_state_bricks_ignored": sorted(observation_state_bricks),
            "rebalance_bricks": sorted([b for b in rebalance_bricks if b]),
        },
        "warnings": warnings,
        "errors": errors,
    }

    save(OUT, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
