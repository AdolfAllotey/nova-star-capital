import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))
PORTFOLIO_DIR = DATA_DIR / "portfolio"

TARGET_PATH = PORTFOLIO_DIR / "portfolio_target.json"
STATE_PATH = PORTFOLIO_DIR / "state" / "portfolio_state.json"
REBALANCE_PATH = PORTFOLIO_DIR / "rebalance" / "rebalance_plan.json"
FUNDING_PATH = PORTFOLIO_DIR / "rebalance" / "funding_plan.json"
OUTPUT_PATH = PORTFOLIO_DIR / "audit" / "aggregator_audit.json"

def now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def approx(a, b, tol=1e-6):
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False

def run_aggregator_audit():
    target = load_json(TARGET_PATH)
    state = load_json(STATE_PATH)
    rebalance = load_json(REBALANCE_PATH)
    funding = load_json(FUNDING_PATH)

    anomalies = []
    warnings = []
    checks = {}

    target_weights = target.get("final_brick_weights", {}) or {}
    state_bricks = state.get("bricks", {}) or {}
    rebalance_actions = rebalance.get("actions", []) or []
    funding_pools = funding.get("funding_pools", []) or []

    # 1) Artifacts
    missing = []
    for name, doc in {
        "portfolio_target": target,
        "portfolio_state": state,
        "rebalance_plan": rebalance,
        "funding_plan": funding,
    }.items():
        if not doc:
            missing.append(name)

    checks["artifacts_ok"] = not missing
    if missing:
        anomalies.append({"type": "missing_artifacts", "details": missing})

    # 2) Target vs state
    mismatches = []
    for brick, target_weight in target_weights.items():
        state_weight = (state_bricks.get(brick) or {}).get("target_weight_snapshot")
        if state_weight is None:
            mismatches.append({"brick": brick, "issue": "missing_state_target_weight"})
        elif not approx(target_weight, state_weight):
            mismatches.append({
                "brick": brick,
                "target_weight": target_weight,
                "state_weight": state_weight,
                "issue": "target_state_mismatch"
            })

    checks["target_state_alignment_ok"] = not mismatches
    if mismatches:
        anomalies.append({"type": "target_state_alignment", "details": mismatches})

    # 3) Allocation sanity
    total_final_weight = float(target.get("total_final_weight", 0.0) or 0.0)
    cash_buffer = float(target.get("cash_buffer", 0.0) or 0.0)
    sum_with_cash = round(total_final_weight + cash_buffer, 6)

    allocation_issues = []
    if total_final_weight > 1.0 + 1e-6:
        allocation_issues.append({"issue": "total_final_weight_above_1", "value": total_final_weight})
    if cash_buffer < -1e-6:
        allocation_issues.append({"issue": "negative_cash_buffer", "value": cash_buffer})
    if not approx(sum_with_cash, 1.0):
        warnings.append({"type": "cash_buffer_sum_not_1", "sum_with_cash": sum_with_cash})

    checks["allocation_ok"] = not allocation_issues
    if allocation_issues:
        anomalies.append({"type": "allocation_sanity", "details": allocation_issues})

    # 4) Rebalance current schema
    rebalance_issues = []
    proposed_actions = [a for a in rebalance_actions if a.get("status") == "proposed"]
    deferred_actions = [a for a in rebalance_actions if a.get("status") == "deferred"]

    for a in rebalance_actions:
        brick = a.get("brick")
        delta = float(a.get("delta_amount_eur", 0.0) or 0.0)
        proposed = float(a.get("proposed_delta_amount_eur", 0.0) or 0.0)

        if abs(proposed) > abs(delta) + 1e-6:
            rebalance_issues.append({
                "brick": brick,
                "issue": "proposed_delta_exceeds_delta",
                "delta_amount_eur": delta,
                "proposed_delta_amount_eur": proposed
            })

        if a.get("status") == "deferred" and abs(proposed) > 1e-6:
            rebalance_issues.append({
                "brick": brick,
                "issue": "deferred_action_has_non_zero_proposed_delta"
            })

    checks["rebalance_ok"] = not rebalance_issues
    if rebalance_issues:
        anomalies.append({"type": "rebalance_consistency", "details": rebalance_issues})

    # 5) Funding current schema
    funding_issues = []
    proposed_by_pool = {}
    for a in proposed_actions:
        pool = a.get("funding_pool", "unknown")
        proposed_by_pool[pool] = proposed_by_pool.get(pool, 0.0) + float(a.get("proposed_delta_amount_eur", 0.0) or 0.0)

    funding_by_pool = {
        p.get("pool"): float(p.get("net_required_eur", 0.0) or 0.0)
        for p in funding_pools
    }

    for pool, expected in proposed_by_pool.items():
        actual = funding_by_pool.get(pool, 0.0)
        if not approx(round(expected, 6), round(actual, 6)):
            funding_issues.append({
                "pool": pool,
                "issue": "funding_pool_net_required_mismatch",
                "expected": round(expected, 6),
                "actual": round(actual, 6)
            })

    checks["funding_ok"] = not funding_issues
    if funding_issues:
        anomalies.append({"type": "funding_consistency", "details": funding_issues})

    governance_ok = all(checks.values())

    audit = {
        "status": "ok" if governance_ok else "warning",
        "engine": "aggregator_audit_v2_current_schema",
        "timestamp": now(),
        "data_dir": str(DATA_DIR),
        "portfolio_regime": target.get("portfolio_regime", "unknown"),
        "governance_ok": governance_ok,
        "checks": checks,
        "portfolio_checks": {
            "total_final_weight": total_final_weight,
            "cash_buffer": cash_buffer,
            "sum_with_cash": sum_with_cash,
            "bricks_count": len(target_weights),
            "state_bricks_count": len(state_bricks),
        },
        "rebalance_summary": {
            "actions_total": len(rebalance_actions),
            "actions_proposed": len(proposed_actions),
            "actions_deferred": len(deferred_actions),
        },
        "funding_summary": {
            "funding_pools": funding_by_pool,
            "manual_approval_required": funding.get("manual_approval_required"),
            "execution_allowed": funding.get("execution_allowed"),
        },
        "anomalies": anomalies,
        "warnings": warnings,
        "notes": [
            "Audit aligned with current preprod schema.",
            "Simulation-only: no execution triggered.",
            "Manual funding rule preserved."
        ],
    }

    save_json(OUTPUT_PATH, audit)
    return audit

if __name__ == "__main__":
    print(json.dumps(run_aggregator_audit(), indent=2, ensure_ascii=False))
