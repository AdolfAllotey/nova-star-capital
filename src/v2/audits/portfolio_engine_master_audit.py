from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PREPROD = Path("/opt/nsc/data/preprod")
PORTFOLIO = PREPROD / "portfolio"
INPUTS = PORTFOLIO / "inputs"

TARGET_PATH = PORTFOLIO / "portfolio_target.json"
STATE_PATH = PORTFOLIO / "state/portfolio_state.json"
POLICY_PATH = PORTFOLIO / "policy/allocation_policy.json"
REBALANCE_PATH = PORTFOLIO / "rebalance/rebalance_plan.json"

OUTPUT = (
    PREPROD
    / "audits"
    / "portfolio_engine_master_audit.json"
)

INPUT_PATHS = {
    "crypto": INPUTS / "crypto_portfolio_input.json",
    "equities_offensive": (
        INPUTS
        / "equities_offensive_portfolio_input.json"
    ),
    "equities_defensive": (
        INPUTS
        / "equities_defensive_portfolio_input.json"
    ),
    "bonds": INPUTS / "bonds_portfolio_input.json",
    "precious_metals": (
        INPUTS
        / "precious_metals_portfolio_input.json"
    ),
    "options_us": (
        INPUTS
        / "options_us_portfolio_input.json"
    ),
}

EXPECTED_ROLES = {
    "crypto": "alpha_aggressive",
    "equities_offensive": "alpha_directional",
    "equities_defensive": "stabilization",
    "bonds": "macro_stabilizer",
    "precious_metals": "systemic_hedge",
}

EXPECTED_POOLS = {
    "crypto": "crypto_exchange_pool",
    "equities_offensive": "ibkr_pool",
    "equities_defensive": "ibkr_pool",
    "bonds": "ibkr_pool",
    "precious_metals": "ibkr_pool",
}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(
    path: Path,
    default: Any = None,
) -> Any:
    try:
        if not path.exists():
            return default

        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return default


def add_failure(
    failures: list,
    check: str,
    severity: str,
    detail: str,
    evidence: Any,
) -> None:
    failures.append({
        "check": check,
        "ok": False,
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    })


target = read_json(TARGET_PATH, {}) or {}
state = read_json(STATE_PATH, {}) or {}
policy = read_json(POLICY_PATH, {}) or {}
rebalance = read_json(REBALANCE_PATH, {}) or {}

inputs = {
    brick: read_json(path, {}) or {}
    for brick, path in INPUT_PATHS.items()
}

failed_checks = []

missing_artifacts = []

for name, path in {
    "portfolio_target": TARGET_PATH,
    "portfolio_state": STATE_PATH,
    "allocation_policy": POLICY_PATH,
    "rebalance_plan": REBALANCE_PATH,
    **{
        f"input_{brick}": path
        for brick, path in INPUT_PATHS.items()
    },
}.items():
    if not path.exists():
        missing_artifacts.append({
            "artifact": name,
            "path": str(path),
        })

if missing_artifacts:
    add_failure(
        failed_checks,
        "required_artifacts",
        "critical",
        "Required Portfolio Brain artifacts are missing.",
        missing_artifacts,
    )

final_weights = (
    target.get("final_brick_weights", {})
    if isinstance(target, dict)
    else {}
)

roles = (
    target.get("brick_roles", {})
    if isinstance(target, dict)
    else {}
)

regimes = (
    target.get("brick_regimes", {})
    if isinstance(target, dict)
    else {}
)

families = (
    target.get("brick_families", {})
    if isinstance(target, dict)
    else {}
)

excluded_rows = (
    target.get("inputs_excluded", [])
    if isinstance(target, dict)
    else []
)

excluded_inputs = {
    row.get("brick"): row.get("reason")
    for row in excluded_rows
    if isinstance(row, dict) and row.get("brick")
}

input_freshness = (
    target.get("input_freshness", {})
    if isinstance(target, dict)
    else {}
)

stale_inputs = (
    target.get("stale_inputs", [])
    if isinstance(target, dict)
    else []
)

cash_buffer = float(
    target.get("cash_buffer", 0.0) or 0.0
)

cash_min = float(
    policy.get("cash_buffer_min_pct", 0.0) or 0.0
)

total_final_weight = round(
    sum(
        float(value or 0.0)
        for value in final_weights.values()
    ),
    6,
)

investable_limit = round(
    1.0 - cash_min,
    6,
)

if policy.get("source_of_truth") is not True:
    add_failure(
        failed_checks,
        "policy_source_of_truth",
        "critical",
        "Allocation policy is not marked as source of truth.",
        {
            "policy_path": str(POLICY_PATH),
            "source_of_truth": policy.get(
                "source_of_truth"
            ),
        },
    )

if stale_inputs:
    add_failure(
        failed_checks,
        "portfolio_input_freshness",
        "critical",
        "Stale inputs were accepted by the governed target.",
        stale_inputs,
    )

if total_final_weight > investable_limit + 0.000001:
    add_failure(
        failed_checks,
        "investable_limit",
        "critical",
        "Final target exceeds the investable policy limit.",
        {
            "total_final_weight": total_final_weight,
            "investable_limit": investable_limit,
        },
    )

if cash_buffer + 0.000001 < cash_min:
    add_failure(
        failed_checks,
        "cash_buffer_minimum",
        "critical",
        "Final cash buffer is below policy minimum.",
        {
            "cash_buffer": cash_buffer,
            "cash_buffer_min_pct": cash_min,
        },
    )

if abs(
    total_final_weight + cash_buffer - 1.0
) > 0.0005:
    add_failure(
        failed_checks,
        "portfolio_total",
        "critical",
        "Final governed weights plus cash do not equal 100%.",
        {
            "total_final_weight": total_final_weight,
            "cash_buffer": cash_buffer,
            "total": round(
                total_final_weight + cash_buffer,
                6,
            ),
        },
    )

for brick, expected_role in EXPECTED_ROLES.items():
    actual = roles.get(brick)

    if actual != expected_role:
        add_failure(
            failed_checks,
            f"{brick}_role",
            "warning",
            f"{brick} role mismatch.",
            {
                "expected": expected_role,
                "actual": actual,
            },
        )

for brick, expected_pool in EXPECTED_POOLS.items():
    input_payload = inputs.get(brick, {})
    actual_pool = input_payload.get("funding_pool")

    if actual_pool != expected_pool:
        add_failure(
            failed_checks,
            f"{brick}_funding_pool",
            "warning",
            f"{brick} funding pool mismatch.",
            {
                "expected": expected_pool,
                "actual": actual_pool,
            },
        )

required_bricks = set(EXPECTED_ROLES)
actual_bricks = set(final_weights)

missing_bricks = sorted(
    required_bricks - actual_bricks
)

unexpected_bricks = sorted(
    actual_bricks - required_bricks
)

if missing_bricks:
    add_failure(
        failed_checks,
        "required_governed_bricks",
        "critical",
        "Required RC1 bricks are missing from the governed target.",
        {
            "missing": missing_bricks,
            "actual": sorted(actual_bricks),
        },
    )

if unexpected_bricks:
    add_failure(
        failed_checks,
        "unexpected_governed_bricks",
        "critical",
        "Unexpected bricks are present in the RC1 governed target.",
        {
            "unexpected": unexpected_bricks,
            "actual": sorted(actual_bricks),
        },
    )

if excluded_inputs.get("options_us") != (
    "not_allowed_by_master_policy"
):
    add_failure(
        failed_checks,
        "options_us_rc1_exclusion",
        "critical",
        "Options US is not correctly excluded from RC1 allocation.",
        {
            "actual_reason": excluded_inputs.get(
                "options_us"
            ),
        },
    )

if excluded_inputs.get("options_v2_shadow") != (
    "shadow_observation_only"
):
    add_failure(
        failed_checks,
        "options_v2_shadow_exclusion",
        "critical",
        "Options V2 Shadow is not correctly classified.",
        {
            "actual_reason": excluded_inputs.get(
                "options_v2_shadow"
            ),
        },
    )

state_bricks = (
    state.get("bricks", {})
    if isinstance(state, dict)
    else {}
)

for brick, reason in excluded_inputs.items():
    state_entry = state_bricks.get(brick, {})

    if not state_entry:
        add_failure(
            failed_checks,
            f"{brick}_state_observation",
            "warning",
            "Excluded brick is absent from the observation state.",
            {
                "brick": brick,
                "reason": reason,
            },
        )
        continue

    target_snapshot = float(
        state_entry.get(
            "target_weight_snapshot",
            0.0,
        )
        or 0.0
    )

    if target_snapshot != 0.0:
        add_failure(
            failed_checks,
            f"{brick}_zero_governed_target",
            "critical",
            "Excluded brick retains a non-zero governed target in state.",
            {
                "target_weight_snapshot": (
                    target_snapshot
                ),
                "status": state_entry.get("status"),
            },
        )

rebalance_bricks = {
    row.get("brick")
    for row in rebalance.get("actions", [])
    if isinstance(row, dict) and row.get("brick")
}

if rebalance_bricks != actual_bricks:
    add_failure(
        failed_checks,
        "rebalance_target_alignment",
        "critical",
        "Rebalance actions do not match governed target bricks.",
        {
            "target_bricks": sorted(actual_bricks),
            "rebalance_bricks": sorted(
                rebalance_bricks
            ),
        },
    )

regime_counter = Counter(
    value
    for value in regimes.values()
    if isinstance(value, str)
)

status = "ok"

if any(
    row.get("severity") == "critical"
    for row in failed_checks
):
    status = "critical"
elif failed_checks:
    status = "warning"

summary = {
    "engine": target.get("engine"),
    "portfolio_regime": target.get(
        "portfolio_regime"
    ),
    "governed_weights": final_weights,
    "governed_roles": roles,
    "governed_families": families,
    "governed_regimes": regimes,
    "regime_distribution": dict(regime_counter),
    "total_final_weight": total_final_weight,
    "cash_buffer": cash_buffer,
    "cash_buffer_min_pct": cash_min,
    "total_with_cash": round(
        total_final_weight + cash_buffer,
        6,
    ),
    "active_governed_bricks": sorted(
        actual_bricks
    ),
    "excluded_inputs": excluded_inputs,
    "input_freshness": input_freshness,
    "stale_inputs": stale_inputs,
    "rebalance_bricks": sorted(
        rebalance_bricks
    ),
}

result = {
    "generated_at": utc_now(),
    "status": status,
    "engine": "portfolio_engine_master_audit_v2",
    "env": "PREPROD",
    "master_intent": {
        "mission": (
            "Validate the governed NSC multi-strategy "
            "portfolio target and its downstream alignment."
        ),
        "preprod_mode": "virtual / simulated only",
        "source_of_truth": str(TARGET_PATH),
    },
    "paths": {
        "portfolio_target": str(TARGET_PATH),
        "portfolio_state": str(STATE_PATH),
        "allocation_policy": str(POLICY_PATH),
        "rebalance_plan": str(REBALANCE_PATH),
        "inputs": {
            brick: str(path)
            for brick, path in INPUT_PATHS.items()
        },
    },
    "summary": summary,
    "failed_checks": failed_checks,
}

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT.write_text(
    json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "status": status,
            "engine": result["engine"],
            "summary": summary,
            "failed_checks": failed_checks,
        },
        indent=2,
        ensure_ascii=False,
    )
)

if status == "critical":
    raise SystemExit(1)
