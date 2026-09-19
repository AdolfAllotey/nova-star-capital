from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")

OUTPUT = (
    DATA
    / "audits"
    / "dashboard_v4_coherence_audit.json"
)

DASHBOARD = (
    ROOT
    / "src"
    / "v2"
    / "interface"
    / "react"
    / "src"
    / "pages"
    / "Dashboard.jsx"
)

PORTFOLIO_TARGET = (
    PREPROD
    / "portfolio"
    / "portfolio_target.json"
)

PORTFOLIO_STATE = (
    PREPROD
    / "portfolio"
    / "state"
    / "portfolio_state.json"
)

REQUIRED_FETCHES = {
    "/dashboard/v3",
    "/api/portfolio-state",
    "/api/portfolio-target",
    "/dashboard/market_regime",
}

EXPECTED_TACTICAL = {
    "bonds",
    "crypto",
    "equities_defensive",
    "equities_offensive",
    "options_us",
    "precious_metals",
}

LEGACY_OPTIONS_IDENTITIES = {
    "options_v2_shadow",
    "options_v3_shadow",
}

MAX_SOURCE_AGE_SECONDS = 259200


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        return {
            "__error__": str(exc),
            "__path__": str(path),
        }

    if not isinstance(value, dict):
        return {
            "__error__": "json_root_not_object",
            "__path__": str(path),
        }

    return value


def document_age_seconds(
    path: Path,
    doc: dict[str, Any],
) -> float | None:
    candidates = [
        doc.get("generated_at"),
        doc.get("timestamp"),
        doc.get("updated_at"),
        doc.get("as_of"),
    ]

    for raw in candidates:
        if not raw:
            continue

        try:
            parsed = datetime.fromisoformat(
                str(raw).replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            age = (
                datetime.now(timezone.utc)
                - parsed.astimezone(timezone.utc)
            ).total_seconds()

            if age < -300:
                return None

            return max(0.0, age)
        except Exception:
            continue

    try:
        mtime = datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=timezone.utc,
        )

        age = (
            datetime.now(timezone.utc) - mtime
        ).total_seconds()

        if age < -300:
            return None

        return max(0.0, age)
    except Exception:
        return None


def add_failure(
    failed: list[dict[str, Any]],
    *,
    check: str,
    detail: str,
    evidence: Any = None,
    severity: str = "critical",
) -> None:
    row = {
        "check": check,
        "severity": severity,
        "detail": detail,
    }

    if evidence is not None:
        row["evidence"] = evidence

    failed.append(row)


dashboard_text = (
    DASHBOARD.read_text(encoding="utf-8")
    if DASHBOARD.exists()
    else ""
)

target = (
    read_json(PORTFOLIO_TARGET)
    if PORTFOLIO_TARGET.exists()
    else {
        "__error__": "missing",
        "__path__": str(PORTFOLIO_TARGET),
    }
)

state = (
    read_json(PORTFOLIO_STATE)
    if PORTFOLIO_STATE.exists()
    else {
        "__error__": "missing",
        "__path__": str(PORTFOLIO_STATE),
    }
)

failed: list[dict[str, Any]] = []

if not DASHBOARD.exists():
    add_failure(
        failed,
        check="dashboard_source_exists",
        detail="Current Dashboard.jsx source is missing.",
        evidence=str(DASHBOARD),
    )

for endpoint in sorted(REQUIRED_FETCHES):
    if endpoint not in dashboard_text:
        add_failure(
            failed,
            check="dashboard_fetches_required_endpoint",
            detail=(
                "Current Dashboard.jsx does not consume "
                f"{endpoint}."
            ),
            evidence=endpoint,
        )

if "__error__" in target:
    add_failure(
        failed,
        check="portfolio_target_readable",
        detail="Canonical portfolio target is unavailable.",
        evidence=target,
    )

if "__error__" in state:
    add_failure(
        failed,
        check="portfolio_state_readable",
        detail="Canonical portfolio state is unavailable.",
        evidence=state,
    )

final_weights = (
    target.get("final_brick_weights")
    or target.get("brick_weights")
    or {}
)

bricks = state.get("bricks") or {}

target_keys = (
    set(final_weights)
    if isinstance(final_weights, dict)
    else set()
)

state_keys = (
    set(bricks)
    if isinstance(bricks, dict)
    else set()
)

if target_keys != EXPECTED_TACTICAL:
    add_failure(
        failed,
        check="portfolio_target_exact_identity",
        detail=(
            "Portfolio target must expose exactly the "
            "six canonical tactical bricks."
        ),
        evidence=sorted(target_keys),
    )

if state_keys != EXPECTED_TACTICAL:
    add_failure(
        failed,
        check="portfolio_state_exact_identity",
        detail=(
            "Portfolio state must expose exactly the "
            "six canonical tactical bricks."
        ),
        evidence=sorted(state_keys),
    )

legacy_in_target = sorted(
    target_keys & LEGACY_OPTIONS_IDENTITIES
)

legacy_in_state = sorted(
    state_keys & LEGACY_OPTIONS_IDENTITIES
)

if legacy_in_target or legacy_in_state:
    add_failure(
        failed,
        check="legacy_options_identity_absent",
        detail=(
            "Legacy Options identities must not appear "
            "in current portfolio contracts."
        ),
        evidence={
            "target": legacy_in_target,
            "state": legacy_in_state,
        },
    )

for brick in sorted(EXPECTED_TACTICAL):
    if brick not in final_weights:
        continue

    state_entry = (
        bricks.get(brick)
        if isinstance(bricks, dict)
        else None
    ) or {}

    state_weight = state_entry.get(
        "target_weight_snapshot"
    )

    if state_weight is None:
        add_failure(
            failed,
            check="state_contains_target_weight_snapshot",
            detail=(
                f"{brick} has no target_weight_snapshot "
                "in portfolio state."
            ),
            evidence=state_entry,
        )
        continue

    try:
        target_weight = float(
            final_weights.get(brick) or 0.0
        )
        state_weight_value = float(
            state_weight or 0.0
        )
    except Exception:
        add_failure(
            failed,
            check="target_state_weight_numeric",
            detail=(
                f"{brick} target/state weight is not numeric."
            ),
            evidence={
                "target": final_weights.get(brick),
                "state": state_weight,
            },
        )
        continue

    if abs(
        target_weight - state_weight_value
    ) > 0.000001:
        add_failure(
            failed,
            check="target_state_weight_match",
            detail=(
                f"{brick} target/state snapshot mismatch."
            ),
            evidence={
                "target": target_weight,
                "state": state_weight_value,
            },
        )

target_regime = target.get("portfolio_regime")
state_regime = state.get("portfolio_regime")

if (
    not target_regime
    or not state_regime
    or str(target_regime) != str(state_regime)
):
    add_failure(
        failed,
        check="portfolio_regime_match",
        detail=(
            "Portfolio target and state regimes must match."
        ),
        evidence={
            "target": target_regime,
            "state": state_regime,
        },
    )

target_age = document_age_seconds(
    PORTFOLIO_TARGET,
    target,
)

state_age = document_age_seconds(
    PORTFOLIO_STATE,
    state,
)

if (
    target_age is None
    or target_age > MAX_SOURCE_AGE_SECONDS
):
    add_failure(
        failed,
        check="portfolio_target_fresh",
        detail=(
            "Canonical portfolio target is stale or "
            "has invalid freshness metadata."
        ),
        evidence={
            "age_seconds": target_age,
            "max_age_seconds":
                MAX_SOURCE_AGE_SECONDS,
        },
    )

if (
    state_age is None
    or state_age > MAX_SOURCE_AGE_SECONDS
):
    add_failure(
        failed,
        check="portfolio_state_fresh",
        detail=(
            "Canonical portfolio state is stale or "
            "has invalid freshness metadata."
        ),
        evidence={
            "age_seconds": state_age,
            "max_age_seconds":
                MAX_SOURCE_AGE_SECONDS,
        },
    )

dashboard_has_legacy_identity = any(
    legacy in dashboard_text
    for legacy in LEGACY_OPTIONS_IDENTITIES
)

if dashboard_has_legacy_identity:
    add_failure(
        failed,
        check="dashboard_source_legacy_options_absent",
        detail=(
            "Current Dashboard.jsx must not reference "
            "legacy Options identities."
        ),
    )

status = "ok"

if any(
    row.get("severity") == "critical"
    for row in failed
):
    status = "critical"
elif failed:
    status = "warning"

result = {
    "generated_at": utc_now(),
    "status": status,
    "engine": (
        "dashboard_production_readiness_audit_v1"
    ),
    "compatibility_artifact": (
        "dashboard_v4_coherence_audit.json"
    ),
    "summary": {
        "dashboard_source": str(DASHBOARD),
        "dashboard_exists": DASHBOARD.exists(),
        "required_fetches": {
            endpoint: endpoint in dashboard_text
            for endpoint in sorted(REQUIRED_FETCHES)
        },
        "portfolio_target_status":
            target.get("status"),
        "portfolio_state_status":
            state.get("status"),
        "portfolio_target_regime":
            target_regime,
        "portfolio_state_regime":
            state_regime,
        "final_brick_weights":
            final_weights,
        "target_bricks":
            sorted(target_keys),
        "state_bricks":
            sorted(state_keys),
        "target_age_seconds":
            None
            if target_age is None
            else round(target_age, 3),
        "state_age_seconds":
            None
            if state_age is None
            else round(state_age, 3),
        "max_source_age_seconds":
            MAX_SOURCE_AGE_SECONDS,
        "legacy_options_identity_in_dashboard":
            dashboard_has_legacy_identity,
    },
    "failed_checks": failed,
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
    ),
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "status": status,
            "engine": result["engine"],
            "summary": result["summary"],
            "failed_checks": failed,
        },
        indent=2,
        ensure_ascii=False,
    )
)
