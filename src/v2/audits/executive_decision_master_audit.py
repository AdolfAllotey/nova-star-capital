from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os


BASE = Path(
    os.getenv(
        "NSC_DATA_DIR",
        "/opt/nsc/data/preprod",
    )
)

EXECUTIVE_PATH = (
    BASE
    / "executive_decision"
    / "executive_decision.json"
)

OUT = (
    BASE
    / "portfolio"
    / "audit"
    / "executive_decision_master_audit.json"
)


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


def main() -> int:
    executive = read_json(
        EXECUTIVE_PATH,
        {},
    )

    failed_checks: list[str] = []
    warnings: list[str] = []

    if not executive:
        failed_checks.append(
            "executive_artifact_missing_or_empty"
        )

    if executive.get("engine") != (
        "executive_decision_engine_v2"
    ):
        failed_checks.append(
            "unexpected_executive_engine"
        )

    required_fields = [
        "decision",
        "decision_confidence",
        "decision_confidence_pct",
        "portfolio_posture",
        "execution_posture",
        "governance_posture",
        "risk_posture",
        "action_policy",
        "execution_allowed",
        "manual_approval_required",
        "governed_brick_decisions",
        "source_freshness",
        "waterfall",
        "drivers",
    ]

    for field in required_fields:
        if field not in executive:
            failed_checks.append(
                f"missing_field_{field}"
            )

    confidence = safe_float(
        executive.get(
            "decision_confidence"
        ),
        -1.0,
    )

    if not 0.0 <= confidence <= 1.0:
        failed_checks.append(
            "decision_confidence_outside_0_1"
        )

    confidence_pct = safe_float(
        executive.get(
            "decision_confidence_pct"
        ),
        -1.0,
    )

    expected_pct = round(
        confidence * 100,
        2,
    )

    if abs(
        confidence_pct - expected_pct
    ) > 0.01:
        failed_checks.append(
            "confidence_pct_mismatch"
        )

    action_policy = str(
        executive.get("action_policy")
        or ""
    ).upper()

    execution_allowed = bool(
        executive.get("execution_allowed")
    )

    execution_posture = str(
        executive.get("execution_posture")
        or ""
    ).upper()

    if (
        action_policy == "SIMULATED_ONLY"
        and execution_allowed
    ):
        failed_checks.append(
            "real_execution_allowed_under_simulated_only"
        )

    if (
        action_policy == "SIMULATED_ONLY"
        and execution_posture
        != "SIMULATED_ONLY"
    ):
        failed_checks.append(
            "simulated_only_posture_not_propagated"
        )

    source_freshness = (
        executive.get("source_freshness")
        or {}
    )

    critical_sources = [
        "portfolio_target",
        "portfolio_state",
        "rebalance_plan",
        "allocation_policy",
        "governance",
    ]

    for source in critical_sources:
        record = (
            source_freshness.get(source)
            or {}
        )

        if not record.get("exists"):
            failed_checks.append(
                f"critical_source_missing_{source}"
            )

        if record.get("stale"):
            failed_checks.append(
                f"critical_source_stale_{source}"
            )

    brick_decisions = (
        executive.get(
            "governed_brick_decisions"
        )
        or {}
    )

    # Governed bricks must follow the current Portfolio Engine target,
    # not a static RC inventory. Disabled and observation-only bricks
    # must not become mandatory simply because they exist in the system.
    portfolio_target_path = Path(
        "/opt/nsc/data/preprod/portfolio/portfolio_target.json"
    )

    portfolio_target = {}
    if portfolio_target_path.exists():
        try:
            portfolio_target = json.loads(
                portfolio_target_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            portfolio_target = {}

    final_brick_weights = (
        portfolio_target.get("final_brick_weights")
        or {}
    )

    expected_bricks = set(
        final_brick_weights.keys()
    )

    missing_bricks = sorted(
        expected_bricks
        - set(brick_decisions)
    )

    if missing_bricks:
        failed_checks.append(
            "missing_governed_bricks:"
            + ",".join(missing_bricks)
        )

    forbidden_bricks = {
        "options_v2_shadow",
        "options_v3_shadow",
        "long_term",
    }

    improperly_governed = sorted(
        forbidden_bricks
        & set(brick_decisions)
    )

    if improperly_governed:
        failed_checks.append(
            "observation_bricks_present_as_governed:"
            + ",".join(improperly_governed)
        )

    governance_rows = [
        row
        for row in executive.get(
            "waterfall",
            [],
        )
        if isinstance(row, dict)
        and row.get("step") == "Governance"
    ]

    if not governance_rows:
        failed_checks.append(
            "governance_waterfall_missing"
        )

    elif governance_rows[0].get(
        "status"
    ) == "PASS" and action_policy == (
        "SIMULATED_ONLY"
    ):
        warnings.append(
            "governance_pass_should_expose_execution_restriction"
        )

    generated_at = executive.get(
        "generated_at"
    )

    age_hours = None

    try:
        generated_dt = datetime.fromisoformat(
            str(generated_at).replace(
                "Z",
                "+00:00",
            )
        )

        if generated_dt.tzinfo is None:
            generated_dt = (
                generated_dt.replace(
                    tzinfo=timezone.utc
                )
            )

        age_hours = (
            datetime.now(timezone.utc)
            - generated_dt
        ).total_seconds() / 3600.0

        if age_hours > 24.0:
            failed_checks.append(
                "executive_artifact_stale"
            )
    except Exception:
        failed_checks.append(
            "invalid_generated_at"
        )

    status = (
        "ok"
        if not failed_checks
        else "failed"
    )

    payload = {
        "status": status,
        "engine": (
            "executive_decision_master_audit_v1"
        ),
        "generated_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "summary": {
            "executive_engine": (
                executive.get("engine")
            ),
            "decision": (
                executive.get("decision")
            ),
            "decision_confidence": (
                executive.get(
                    "decision_confidence"
                )
            ),
            "portfolio_posture": (
                executive.get(
                    "portfolio_posture"
                )
            ),
            "execution_posture": (
                executive.get(
                    "execution_posture"
                )
            ),
            "governance_posture": (
                executive.get(
                    "governance_posture"
                )
            ),
            "risk_posture": (
                executive.get(
                    "risk_posture"
                )
            ),
            "action_policy": (
                executive.get(
                    "action_policy"
                )
            ),
            "execution_allowed": (
                executive.get(
                    "execution_allowed"
                )
            ),
            "artifact_age_hours": (
                None
                if age_hours is None
                else round(
                    age_hours,
                    4,
                )
            ),
            "governed_bricks": sorted(
                brick_decisions
            ),
        },
        "warnings": warnings,
        "failed_checks": failed_checks,
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

    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0 if not failed_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
