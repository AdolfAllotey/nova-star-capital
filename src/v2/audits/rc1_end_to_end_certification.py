from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import math
import os


BASE = Path(
    os.getenv(
        "NSC_DATA_DIR",
        "/opt/nsc/data/preprod",
    )
)

APP = Path(
    os.getenv(
        "NSC_APP_DIR",
        "/opt/nsc/app",
    )
)

OUT = (
    BASE
    / "portfolio"
    / "audit"
    / "rc1_end_to_end_certification.json"
)

HISTORY = (
    BASE
    / "portfolio"
    / "audit"
    / "rc1_end_to_end_history.jsonl"
)

PATHS = {
    "portfolio_target": (
        BASE
        / "portfolio"
        / "portfolio_target.json"
    ),
    "portfolio_state": (
        BASE
        / "portfolio"
        / "state"
        / "portfolio_state.json"
    ),
    "rebalance_plan": (
        BASE
        / "portfolio"
        / "rebalance"
        / "rebalance_plan.json"
    ),
    "allocation_policy": (
        BASE
        / "portfolio"
        / "policy"
        / "allocation_policy.json"
    ),
    "governance": (
        BASE
        / "analysis"
        / "governance_engine_pro.json"
    ),
    "executive_decision": (
        BASE
        / "executive_decision"
        / "executive_decision.json"
    ),
    "executive_audit": (
        BASE
        / "portfolio"
        / "audit"
        / "executive_decision_master_audit.json"
    ),
}

OPTIONAL_PATH_GROUPS = {
    "master_coherence": [
        BASE / "portfolio/audit/master_coherence_audit.json",
        BASE / "portfolio/audit/portfolio_master_coherence_audit.json",
        BASE / "portfolio/rebalance/master_coherence_audit.json",
    ],
    "global_orchestration": [
        BASE / "portfolio/audit/global_orchestration_audit.json",
        BASE / "portfolio/audit/global_orchestration_status.json",
        BASE / "portfolio/orchestration/global_orchestration_audit.json",
    ],
    "supervision": [
        BASE / "portfolio/audit/supervision_gate.json",
        BASE / "portfolio/audit/institutional_supervision_summary.json",
        BASE / "portfolio/audit/orchestration_status.json",
    ],
    "portfolio_master_audit": [
        BASE / "portfolio/audit/portfolio_master_audit.json",
        BASE / "portfolio/audit/global_preprod_committee_review.json",
        BASE / "portfolio/audit/global_preprod_master_audit.json",
    ],
}

WRAPPER = APP / "src/v2/run_pipeline_wrapped.py"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_json(
    path: Path,
    default: Any,
) -> Any:
    try:
        if path.exists():
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
    except Exception:
        pass

    return default


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def age_hours(
    path: Path,
) -> float | None:
    if not path.exists():
        return None

    modified = datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=timezone.utc,
    )

    return (
        now_utc() - modified
    ).total_seconds() / 3600.0


def first_existing(
    paths: list[Path],
) -> Path | None:
    for path in paths:
        if path.exists():
            return path

    return None


def normalize_status(
    payload: dict[str, Any],
) -> str:
    candidates = [
        payload.get("status"),
        payload.get("decision"),
        payload.get("result"),
        payload.get("overall_status"),
        payload.get("summary", {}).get("status"),
    ]

    for value in candidates:
        if value is not None:
            return str(value).upper()

    return "UNKNOWN"


def main() -> int:
    generated_at = now_utc().isoformat()

    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []

    def add_check(
        check_id: str,
        status: str,
        evidence: Any,
        blocking: bool = True,
    ) -> None:
        record = {
            "check_id": check_id,
            "status": status,
            "blocking": blocking,
            "evidence": evidence,
        }

        checks.append(record)

        if status == "FAIL":
            if blocking:
                failures.append(check_id)
            else:
                warnings.append(check_id)

    required_payloads: dict[str, dict[str, Any]] = {}

    for name, path in PATHS.items():
        exists = path.exists()
        payload = read_json(path, {})
        required_payloads[name] = payload

        add_check(
            f"FILE-{name}",
            "PASS" if exists and payload else "FAIL",
            {
                "path": str(path),
                "exists": exists,
                "age_hours": (
                    None
                    if age_hours(path) is None
                    else round(
                        age_hours(path) or 0.0,
                        4,
                    )
                ),
                "engine": (
                    payload.get("engine")
                    if isinstance(payload, dict)
                    else None
                ),
            },
        )

    optional_payloads: dict[str, dict[str, Any]] = {}
    optional_paths: dict[str, str | None] = {}

    for name, candidates in OPTIONAL_PATH_GROUPS.items():
        path = first_existing(candidates)

        if path is None:
            optional_payloads[name] = {}
            optional_paths[name] = None

            add_check(
                f"OPTIONAL-{name}",
                "FAIL",
                {
                    "searched_paths": [
                        str(item)
                        for item in candidates
                    ],
                    "reason": "no_candidate_found",
                },
                blocking=False,
            )

            continue

        payload = read_json(path, {})
        optional_payloads[name] = payload
        optional_paths[name] = str(path)

        add_check(
            f"OPTIONAL-{name}",
            "PASS" if payload else "FAIL",
            {
                "path": str(path),
                "age_hours": round(
                    age_hours(path) or 0.0,
                    4,
                ),
                "status": normalize_status(payload),
                "engine": payload.get("engine"),
            },
            blocking=False,
        )

    freshness_limits = {
        "portfolio_target": 1.0,
        "portfolio_state": 1.0,
        "rebalance_plan": 1.0,
        "governance": 1.0,
        "executive_decision": 1.0,
        "executive_audit": 1.0,
        "allocation_policy": 24.0 * 365.0,
    }

    freshness_snapshot = {}

    for name, path in PATHS.items():
        current_age = age_hours(path)
        limit = freshness_limits[name]
        stale = (
            current_age is None
            or current_age > limit
        )

        freshness_snapshot[name] = {
            "path": str(path),
            "age_hours": (
                None
                if current_age is None
                else round(current_age, 4)
            ),
            "limit_hours": limit,
            "stale": stale,
        }

        add_check(
            f"FRESH-{name}",
            "FAIL" if stale else "PASS",
            freshness_snapshot[name],
        )

    target = required_payloads["portfolio_target"]
    state = required_payloads["portfolio_state"]
    rebalance = required_payloads["rebalance_plan"]
    policy = required_payloads["allocation_policy"]
    governance = required_payloads["governance"]
    executive = required_payloads["executive_decision"]
    executive_audit = required_payloads["executive_audit"]

    target_weights = (
        target.get("final_brick_weights")
        or {}
    )

    cash_buffer = safe_float(
        target.get("cash_buffer"),
        0.0,
    )

    governed_total = (
        sum(
            safe_float(value)
            for value in target_weights.values()
        )
        + cash_buffer
    )

    add_check(
        "PORTFOLIO-weights-plus-cash-equals-one",
        (
            "PASS"
            if math.isclose(
                governed_total,
                1.0,
                abs_tol=0.00001,
            )
            else "FAIL"
        ),
        {
            "brick_weights_total": round(
                sum(
                    safe_float(value)
                    for value in target_weights.values()
                ),
                6,
            ),
            "cash_buffer": round(
                cash_buffer,
                6,
            ),
            "total": round(
                governed_total,
                6,
            ),
        },
    )

    expected_governed_bricks = {
        "crypto",
        "equities_offensive",
        "equities_defensive",
        "bonds",
        "precious_metals",
    }

    actual_target_bricks = set(
        target_weights.keys()
    )

    add_check(
        "PORTFOLIO-governed-brick-set",
        (
            "PASS"
            if actual_target_bricks
            == expected_governed_bricks
            else "FAIL"
        ),
        {
            "expected": sorted(
                expected_governed_bricks
            ),
            "actual": sorted(
                actual_target_bricks
            ),
        },
    )

    target_exclusions = {
        item.get("brick"): item.get("reason")
        for item in target.get(
            "inputs_excluded",
            [],
        )
        if isinstance(item, dict)
    }

    add_check(
        "OPTIONS-options-us-excluded",
        (
            "PASS"
            if "options_us" in target_exclusions
            else "FAIL"
        ),
        {
            "inputs_excluded": target_exclusions,
        },
    )

    add_check(
        "OPTIONS-shadow-excluded",
        (
            "PASS"
            if "options_v2_shadow"
            in target_exclusions
            else "FAIL"
        ),
        {
            "inputs_excluded": target_exclusions,
        },
    )

    forbidden_target_bricks = {
        "options_us",
        "options_v2_shadow",
        "options_v3_shadow",
        "long_term",
    }

    forbidden_in_target = sorted(
        forbidden_target_bricks
        & actual_target_bricks
    )

    add_check(
        "OPTIONS-no-observation-brick-in-target",
        (
            "PASS"
            if not forbidden_in_target
            else "FAIL"
        ),
        {
            "forbidden_in_target": (
                forbidden_in_target
            ),
        },
    )

    state_bricks = state.get("bricks") or {}

    governed_state_bricks = {
        name
        for name, row in state_bricks.items()
        if isinstance(row, dict)
        and row.get("governed_target") is True
    }

    add_check(
        "STATE-governed-bricks-match-target",
        (
            "PASS"
            if governed_state_bricks
            == expected_governed_bricks
            else "FAIL"
        ),
        {
            "expected": sorted(
                expected_governed_bricks
            ),
            "actual": sorted(
                governed_state_bricks
            ),
        },
    )

    option_state_checks = {
        name: {
            "status": (
                state_bricks.get(name, {})
                .get("status")
            ),
            "target": safe_float(
                state_bricks.get(name, {})
                .get("target"),
                0.0,
            ),
            "governed_target": (
                state_bricks.get(name, {})
                .get("governed_target")
            ),
        }
        for name in (
            "options_us",
            "options_v2_shadow",
            "options_v3_shadow",
        )
        if name in state_bricks
    }

    invalid_option_state = [
        name
        for name, row in option_state_checks.items()
        if row["target"] != 0.0
        or row["governed_target"] is True
    ]

    add_check(
        "STATE-options-remain-observation-only",
        (
            "PASS"
            if not invalid_option_state
            else "FAIL"
        ),
        {
            "options_state": option_state_checks,
            "invalid": invalid_option_state,
        },
    )

    actions = [
        item
        for item in rebalance.get(
            "actions",
            [],
        )
        if isinstance(item, dict)
    ]

    action_bricks = {
        item.get("brick")
        for item in actions
        if item.get("brick")
    }

    add_check(
        "REBALANCE-actions-only-governed-bricks",
        (
            "PASS"
            if action_bricks
            <= expected_governed_bricks
            else "FAIL"
        ),
        {
            "action_bricks": sorted(
                action_bricks
            ),
            "unexpected": sorted(
                action_bricks
                - expected_governed_bricks
            ),
        },
    )

    proposed_actions = [
        item
        for item in actions
        if str(
            item.get("status")
        ).lower() == "proposed"
    ]

    summary_proposed = int(
        safe_float(
            rebalance.get(
                "summary",
                {},
            ).get("actions_proposed"),
            0.0,
        )
    )

    add_check(
        "REBALANCE-summary-matches-actions",
        (
            "PASS"
            if summary_proposed
            == len(proposed_actions)
            else "FAIL"
        ),
        {
            "summary_actions_proposed": (
                summary_proposed
            ),
            "actual_proposed_actions": (
                len(proposed_actions)
            ),
        },
    )

    action_policy = str(
        governance.get(
            "action_policy"
        )
        or "UNKNOWN"
    ).upper()

    governance_hard_block = bool(
        governance.get("hard_block")
    )

    governance_soft_veto = bool(
        governance.get("soft_veto")
    )

    governance_caps = (
        governance.get("caps")
        or {}
    )

    max_orders = int(
        safe_float(
            governance_caps.get(
                "max_orders_per_run"
            ),
            0.0,
        )
    )

    add_check(
        "GOVERNANCE-policy-present",
        (
            "PASS"
            if action_policy != "UNKNOWN"
            else "FAIL"
        ),
        {
            "action_policy": action_policy,
            "hard_block": governance_hard_block,
            "soft_veto": governance_soft_veto,
            "max_orders_per_run": max_orders,
        },
    )

    rebalance_execution_allowed = bool(
        rebalance.get("execution_allowed")
    )

    if action_policy == "SIMULATED_ONLY":
        add_check(
            "GOVERNANCE-simulated-only-blocks-real-execution",
            (
                "PASS"
                if not rebalance_execution_allowed
                and max_orders == 0
                else "FAIL"
            ),
            {
                "action_policy": action_policy,
                "rebalance_execution_allowed": (
                    rebalance_execution_allowed
                ),
                "max_orders_per_run": max_orders,
            },
        )
    else:
        add_check(
            "GOVERNANCE-simulated-only-blocks-real-execution",
            "PASS",
            {
                "action_policy": action_policy,
                "note": (
                    "SIMULATED_ONLY rule not active "
                    "during this run."
                ),
            },
        )

    add_check(
        "EXECUTIVE-engine-v2",
        (
            "PASS"
            if executive.get("engine")
            == "executive_decision_engine_v2"
            else "FAIL"
        ),
        {
            "engine": executive.get("engine"),
        },
    )

    executive_confidence = safe_float(
        executive.get(
            "decision_confidence"
        ),
        -1.0,
    )

    add_check(
        "EXECUTIVE-confidence-scale-0-1",
        (
            "PASS"
            if 0.0
            <= executive_confidence
            <= 1.0
            else "FAIL"
        ),
        {
            "decision_confidence": (
                executive_confidence
            ),
            "decision_confidence_pct": (
                executive.get(
                    "decision_confidence_pct"
                )
            ),
        },
    )

    executive_bricks = set(
        (
            executive.get(
                "governed_brick_decisions"
            )
            or {}
        ).keys()
    )

    add_check(
        "EXECUTIVE-governed-bricks-match-target",
        (
            "PASS"
            if executive_bricks
            == expected_governed_bricks
            else "FAIL"
        ),
        {
            "expected": sorted(
                expected_governed_bricks
            ),
            "actual": sorted(
                executive_bricks
            ),
        },
    )

    executive_action_policy = str(
        executive.get(
            "action_policy"
        )
        or "UNKNOWN"
    ).upper()

    executive_execution_allowed = bool(
        executive.get(
            "execution_allowed"
        )
    )

    executive_execution_posture = str(
        executive.get(
            "execution_posture"
        )
        or "UNKNOWN"
    ).upper()

    add_check(
        "EXECUTIVE-governance-policy-propagated",
        (
            "PASS"
            if executive_action_policy
            == action_policy
            else "FAIL"
        ),
        {
            "governance_action_policy": (
                action_policy
            ),
            "executive_action_policy": (
                executive_action_policy
            ),
        },
    )

    if action_policy == "SIMULATED_ONLY":
        executive_policy_ok = (
            executive_execution_allowed is False
            and executive_execution_posture
            == "SIMULATED_ONLY"
        )
    else:
        executive_policy_ok = True

    add_check(
        "EXECUTIVE-execution-restriction-propagated",
        (
            "PASS"
            if executive_policy_ok
            else "FAIL"
        ),
        {
            "action_policy": action_policy,
            "execution_allowed": (
                executive_execution_allowed
            ),
            "execution_posture": (
                executive_execution_posture
            ),
        },
    )

    add_check(
        "EXECUTIVE-master-audit-pass",
        (
            "PASS"
            if executive_audit.get("status")
            == "ok"
            and not executive_audit.get(
                "failed_checks"
            )
            else "FAIL"
        ),
        {
            "status": executive_audit.get(
                "status"
            ),
            "failed_checks": executive_audit.get(
                "failed_checks"
            ),
            "warnings": executive_audit.get(
                "warnings"
            ),
        },
    )

    wrapper_text = (
        WRAPPER.read_text(
            encoding="utf-8"
        )
        if WRAPPER.exists()
        else ""
    )

    wrapper_order_tokens = [
        "portfolio_engine",
        "portfolio_state",
        "rebalance",
        "coherence",
        "orchestration",
        "supervision",
        "executive_decision_engine_v2",
        "executive_decision_master_audit",
    ]

    token_positions = {
        token: wrapper_text.find(token)
        for token in wrapper_order_tokens
    }

    missing_wrapper_tokens = [
        token
        for token, position
        in token_positions.items()
        if position < 0
    ]

    add_check(
        "WRAPPER-critical-components-present",
        (
            "PASS"
            if not missing_wrapper_tokens
            else "FAIL"
        ),
        {
            "positions": token_positions,
            "missing": missing_wrapper_tokens,
        },
    )

    executive_position = token_positions.get(
        "executive_decision_engine_v2",
        -1,
    )

    supervision_positions = [
        position
        for token, position
        in token_positions.items()
        if "supervision" in token
        and position >= 0
    ]

    executive_after_supervision = (
        executive_position >= 0
        and bool(supervision_positions)
        and executive_position
        > max(supervision_positions)
    )

    add_check(
        "WRAPPER-executive-after-supervision",
        (
            "PASS"
            if executive_after_supervision
            else "FAIL"
        ),
        {
            "executive_position": (
                executive_position
            ),
            "supervision_positions": (
                supervision_positions
            ),
        },
    )

    optional_statuses = {
        name: normalize_status(payload)
        for name, payload
        in optional_payloads.items()
        if payload
    }

    blocking_optional_statuses = {
        "FAIL",
        "FAILED",
        "BLOCK",
        "BLOCKED",
        "BLOCKING",
        "KO",
        "REJECTED",
    }

    optional_blockers = {
        name: status
        for name, status
        in optional_statuses.items()
        if status
        in blocking_optional_statuses
    }

    add_check(
        "MASTER-no-known-optional-audit-blocker",
        (
            "PASS"
            if not optional_blockers
            else "FAIL"
        ),
        {
            "optional_statuses": (
                optional_statuses
            ),
            "blocking_statuses": (
                optional_blockers
            ),
        },
    )

    final_status = (
        "PASS"
        if not failures
        else "FAIL"
    )

    certification = (
        "RC1_END_TO_END_CERTIFIED"
        if final_status == "PASS"
        else "RC1_END_TO_END_REJECTED"
    )

    payload = {
        "engine": (
            "rc1_end_to_end_certification_v1"
        ),
        "generated_at": generated_at,
        "status": final_status,
        "certification": certification,
        "rc1_blocker": bool(failures),
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(
                1
                for item in checks
                if item["status"] == "PASS"
            ),
            "checks_failed": sum(
                1
                for item in checks
                if item["status"] == "FAIL"
            ),
            "blocking_failures": failures,
            "warnings": warnings,
            "portfolio_regime": (
                target.get(
                    "portfolio_regime"
                )
            ),
            "governed_weights": (
                target_weights
            ),
            "cash_buffer": cash_buffer,
            "action_policy": action_policy,
            "governance_hard_block": (
                governance_hard_block
            ),
            "governance_soft_veto": (
                governance_soft_veto
            ),
            "rebalance_execution_allowed": (
                rebalance_execution_allowed
            ),
            "executive_decision": (
                executive.get("decision")
            ),
            "executive_recommended_brick": (
                executive.get(
                    "recommended_brick"
                )
            ),
            "executive_recommended_amount_eur": (
                executive.get(
                    "recommended_amount_eur"
                )
            ),
            "executive_confidence": (
                executive.get(
                    "decision_confidence"
                )
            ),
            "executive_execution_posture": (
                executive.get(
                    "execution_posture"
                )
            ),
            "executive_risk_posture": (
                executive.get(
                    "risk_posture"
                )
            ),
        },
        "freshness": freshness_snapshot,
        "optional_artifacts": optional_paths,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with HISTORY.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                {
                    "generated_at": generated_at,
                    "status": final_status,
                    "certification": certification,
                    "blocking_failures": failures,
                    "warnings": warnings,
                    "executive_decision": (
                        executive.get(
                            "decision"
                        )
                    ),
                    "executive_confidence": (
                        executive.get(
                            "decision_confidence"
                        )
                    ),
                    "action_policy": (
                        action_policy
                    ),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    print(
        json.dumps(
            {
                "status": final_status,
                "certification": certification,
                "rc1_blocker": bool(failures),
                "checks_total": len(checks),
                "checks_passed": sum(
                    1
                    for item in checks
                    if item["status"]
                    == "PASS"
                ),
                "checks_failed": sum(
                    1
                    for item in checks
                    if item["status"]
                    == "FAIL"
                ),
                "blocking_failures": failures,
                "warnings": warnings,
                "portfolio_regime": (
                    target.get(
                        "portfolio_regime"
                    )
                ),
                "action_policy": action_policy,
                "executive_decision": (
                    executive.get(
                        "decision"
                    )
                ),
                "executive_recommended_brick": (
                    executive.get(
                        "recommended_brick"
                    )
                ),
                "executive_recommended_amount_eur": (
                    executive.get(
                        "recommended_amount_eur"
                    )
                ),
                "executive_confidence": (
                    executive.get(
                        "decision_confidence"
                    )
                ),
                "executive_execution_posture": (
                    executive.get(
                        "execution_posture"
                    )
                ),
                "output": str(OUT),
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
