import json
import os
from datetime import datetime
from pathlib import Path


DEFAULT_DATA_DIR = "/opt/nsc/data/preprod"
DATA_DIR = Path(os.getenv("NSC_DATA_DIR", DEFAULT_DATA_DIR))
PORTFOLIO_DIR = DATA_DIR / "portfolio"

TARGET_PATH = PORTFOLIO_DIR / "portfolio_target.json"
STATE_PATH = PORTFOLIO_DIR / "state" / "portfolio_state.json"
POLICY_PATH = PORTFOLIO_DIR / "policy" / "allocation_policy.json"
OUTPUT_PATH = PORTFOLIO_DIR / "rebalance" / "rebalance_plan.json"


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


def bucket_from_action(action_type: str) -> str:
    if action_type == "reduce":
        return "risk_reduction"
    if action_type == "increase":
        return "capital_deployment"
    return "monitoring"


def compute_priority_score(
    requested_delta: float,
    confidence: float,
    action_type: str,
    regime: str,
    family: str,
    execution_blocked: bool,
) -> float:
    base = abs(requested_delta) * 100.0
    conf_boost = confidence * 10.0

    family_boost = 0.0
    if action_type == "reduce" and family == "offensive":
        family_boost += 10.0
    if action_type == "increase" and family == "macro_defensive":
        family_boost += 6.0
    if action_type == "increase" and family == "systemic_hedge":
        family_boost += 4.0

    regime_boost = 0.0
    regime_norm = str(regime or "").lower()
    if regime_norm == "risk_off" and action_type == "reduce":
        regime_boost += 8.0
    if regime_norm == "risk_off" and action_type == "increase":
        regime_boost -= 4.0

    blocked_penalty = -8.0 if execution_blocked and action_type == "increase" else 0.0

    return round(base + conf_boost + family_boost + regime_boost + blocked_penalty, 3)


def run_rebalance_plan_builder():
    target = load_json(TARGET_PATH)
    state = load_json(STATE_PATH)
    policy = load_json(POLICY_PATH)

    final_brick_weights = target.get("final_brick_weights", {}) or {}
    brick_families = target.get("brick_families", {}) or {}
    brick_roles = target.get("brick_roles", {}) or {}
    brick_states = state.get("bricks", {}) or {}
    brick_inertia = policy.get("brick_inertia", {}) or {}
    inter_pool_rules = policy.get("inter_pool_rules", {}) or {}
    current_mode = policy.get("current_mode", "normal")
    portfolio_regime = target.get("portfolio_regime", state.get("portfolio_regime", "unknown"))

    actions = []

    for brick, fallback_target_weight in final_brick_weights.items():
        state_info = brick_states.get(brick, {}) or {}
        target_weight = float(state_info.get("target_weight_snapshot", fallback_target_weight) or 0.0)
        current_weight = float(state_info.get("current_weight_estimate", target_weight) or 0.0)
        requested_delta = round(target_weight - current_weight, 6)

        inertia = brick_inertia.get(brick, {}) or {}
        min_threshold = float(inertia.get("min_threshold_to_rebalance", 0.03) or 0.03)
        max_change = float(inertia.get("max_weight_change_per_cycle", 0.02) or 0.02)

        family = brick_families.get(brick, "unknown")
        portfolio_role = brick_roles.get(brick, state_info.get("portfolio_role", "unknown"))
        current_pool = state_info.get("funding_pool", "unknown")
        confidence = float(state_info.get("confidence", 0.0) or 0.0)
        execution_blocked = bool((state_info.get("risk_flags") or {}).get("execution_blocked", False))

        constraints_active = []
        status = "deferred"
        approved_delta = 0.0
        action_type = "hold"
        reason = "No significant rebalance required."
        rationale = []
        manual_transfer_required = False
        inter_pool_blocked = False

        if abs(requested_delta) < min_threshold:
            constraints_active.append("below_rebalance_threshold")
            rationale.append(
                f"abs(requested_delta)={abs(requested_delta):.6f} below threshold={min_threshold:.6f}"
            )
        else:
            if requested_delta > 0:
                action_type = "increase"
                reason = "Target weight above current estimated state."
                rationale.append("portfolio needs additional allocation on this brick")
            elif requested_delta < 0:
                action_type = "reduce"
                reason = "Target weight below current estimated state."
                rationale.append("portfolio is overweight versus target on this brick")

            approved_delta = max(-max_change, min(max_change, requested_delta))
            rationale.append(f"requested_delta={requested_delta:.6f}")
            rationale.append(f"max_change_per_cycle={max_change:.6f}")
            rationale.append(f"approved_delta_clipped={approved_delta:.6f}")

            if current_mode == "exit_only" and approved_delta > 0:
                approved_delta = 0.0
                status = "blocked"
                constraints_active.append("policy_exit_only")
                reason = "Increase blocked by policy mode exit_only."
                rationale.append("policy veto: exit_only")
            elif current_mode == "reduce_only" and approved_delta > 0:
                approved_delta = 0.0
                status = "blocked"
                constraints_active.append("policy_reduce_only")
                reason = "Increase blocked by policy mode reduce_only."
                rationale.append("policy veto: reduce_only")
            elif execution_blocked and approved_delta > 0:
                approved_delta = 0.0
                status = "blocked"
                constraints_active.append("brick_execution_blocked")
                reason = "Increase blocked because brick execution is currently blocked."
                rationale.append("brick risk_flags.execution_blocked=true")
            else:
                status = "approved"

        execution_bucket = bucket_from_action(action_type)

        if action_type == "increase" and inter_pool_rules.get("manual_transfer_required", True):
            manual_transfer_required = True
            rationale.append("any future cross-pool funding remains manual-only by policy")

        priority_score = compute_priority_score(
            requested_delta=requested_delta,
            confidence=confidence,
            action_type=action_type,
            regime=portfolio_regime,
            family=family,
            execution_blocked=execution_blocked,
        )

        actions.append({
            "brick": brick,
            "family": family,
            "portfolio_role": portfolio_role,
            "current_pool": current_pool,
            "execution_bucket": execution_bucket,
            "action": action_type,
            "target_weight": round(target_weight, 6),
            "current_weight_estimate": round(current_weight, 6),
            "requested_delta": requested_delta,
            "approved_delta": round(approved_delta, 6),
            "priority_score": priority_score,
            "status": status,
            "reason": reason,
            "rationale": rationale,
            "triggered_by": [
                "portfolio_engine_v1",
                "allocation_policy",
                "portfolio_state_builder_v1_2"
            ],
            "constraints_active": constraints_active,
            "funding_pool": current_pool,
            "state_origin": state_info.get("state_origin", "unknown"),
            "confidence": confidence,
            "manual_transfer_required": manual_transfer_required,
            "inter_pool_blocked": inter_pool_blocked,
        })

    actions = sorted(
        actions,
        key=lambda a: (
            0 if a.get("status") == "approved" else 1,
            -float(a.get("priority_score", 0.0) or 0.0),
            a.get("brick", ""),
        )
    )

    rebalance_plan = {
        "status": "ok",
        "engine": "rebalance_plan_builder_v2",
        "data_dir": str(DATA_DIR),
        "portfolio_regime": portfolio_regime,
        "policy_mode": current_mode,
        "inter_pool_rules": inter_pool_rules,
        "actions": actions,
        "notes": [
            "V2 introduces priority_score, execution_bucket, family context, and rationale.",
            "V2 remains state-estimate driven until broker reconciliation is available.",
            "Cross-pool funding stays governed by manual-only policy."
        ]
    }

    save_json(rebalance_plan, OUTPUT_PATH)
    return rebalance_plan


if __name__ == "__main__":
    result = run_rebalance_plan_builder()
    print(json.dumps(result, indent=2))
