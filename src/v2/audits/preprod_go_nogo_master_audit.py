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
    / "preprod_go_nogo_master_audit.json"
)

AUDITS = {
    "crypto":
        DATA / "audits/crypto_master_strategy_audit.json",

    "equities_offensive":
        DATA / "audits/equities_offensive_master_strategy_audit.json",

    "equities_defensive":
        DATA / "audits/equities_defensive_master_strategy_audit.json",

    "bonds":
        DATA / "audits/bonds_master_strategy_audit.json",

    "precious_metals":
        DATA / "audits/precious_metals_master_strategy_audit.json",

    "options_us":
        DATA / "audits/options_us_master_strategy_audit.json",

    "long_term_global":
        DATA / "audits/long_term_global_master_strategy_audit.json",

    "portfolio_engine":
        PREPROD / "audits/portfolio_engine_master_audit.json",

    "capital_funding":
        DATA / "audits/capital_funding_master_audit.json",

    "dashboard_v4":
        DATA / "audits/dashboard_v4_coherence_audit.json",

    "governance_risk":
        DATA / "audits/governance_risk_master_audit.json",

    "runtime_consistency":
        DATA / "audits/runtime_consistency_audit.json",

    "runtime_telemetry":
        DATA / "audits/runtime_telemetry_audit.json",

    "dynamic_signal_activity":
        DATA / "audits/dynamic_signal_activity_audit.json",

    "rc2_end_to_end":
        PREPROD / "audits/rc2_end_to_end_certification.json",
}


#
# Freshness doctrine
#
# Values are warning / critical thresholds.
#
# Daily strategy and governance certifications:
#     warning > 36h
#     critical > 60h
#
# Options:
#     Mon-Fri operational schedule.
#     Weekend-safe tolerance is required.
#
# Long Term:
#     valuation refreshes frequently, while the global master
#     certification is currently less tightly scheduled.
#
# Portfolio Engine:
#     master runtime is refreshed by the hourly global PREPROD cycle.
#
FRESHNESS_POLICY_SECONDS = {
    "crypto": (36 * 3600, 60 * 3600),
    "equities_offensive": (36 * 3600, 60 * 3600),
    "equities_defensive": (36 * 3600, 60 * 3600),
    "bonds": (36 * 3600, 60 * 3600),
    "precious_metals": (36 * 3600, 60 * 3600),

    "options_us": (72 * 3600, 96 * 3600),

    "long_term_global": (72 * 3600, 96 * 3600),

    "portfolio_engine": (6 * 3600, 12 * 3600),

    "capital_funding": (36 * 3600, 60 * 3600),
    "dashboard_v4": (36 * 3600, 60 * 3600),
    "governance_risk": (36 * 3600, 60 * 3600),
    "runtime_consistency": (36 * 3600, 60 * 3600),
    "runtime_telemetry": (36 * 3600, 60 * 3600),
    "dynamic_signal_activity": (36 * 3600, 60 * 3600),

    "rc2_end_to_end": (36 * 3600, 60 * 3600),
}

TIME_FIELDS = (
    "generated_at",
    "timestamp",
    "updated_at",
    "as_of",
    "ts",
    "created_at",
)

FUTURE_TOLERANCE_SECONDS = 300


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {
                "status": "missing",
                "path": str(path),
            }

        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(value, dict):
            return {
                "status": "error",
                "error": "json_root_not_object",
                "path": str(path),
            }

        return value

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "path": str(path),
        }


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def document_timestamp(
    doc: dict[str, Any],
) -> tuple[str | None, datetime | None]:
    for field in TIME_FIELDS:
        parsed = parse_timestamp(
            doc.get(field)
        )

        if parsed is not None:
            return field, parsed

    return None, None


def evaluate_freshness(
    name: str,
    doc: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:

    warning_after, critical_after = (
        FRESHNESS_POLICY_SECONDS[name]
    )

    field, timestamp = document_timestamp(
        doc
    )

    result: dict[str, Any] = {
        "timestamp_field": field,
        "timestamp": (
            timestamp.isoformat()
            if timestamp is not None
            else None
        ),
        "warning_after_seconds": warning_after,
        "critical_after_seconds": critical_after,
        "future_tolerance_seconds":
            FUTURE_TOLERANCE_SECONDS,
    }

    if timestamp is None:
        result.update({
            "status": "critical",
            "reason": "missing_or_invalid_timestamp",
            "age_seconds": None,
        })
        return result

    age_seconds = (
        now - timestamp
    ).total_seconds()

    result["age_seconds"] = round(
        age_seconds,
        3,
    )

    if age_seconds < -FUTURE_TOLERANCE_SECONDS:
        result.update({
            "status": "critical",
            "reason": "timestamp_in_future",
        })

    elif age_seconds > critical_after:
        result.update({
            "status": "critical",
            "reason": "critical_stale",
        })

    elif age_seconds > warning_after:
        result.update({
            "status": "warning",
            "reason": "warning_stale",
        })

    else:
        result.update({
            "status": "ok",
            "reason": "fresh",
        })

    return result


audit_results = {
    name: read_json(path)
    for name, path in AUDITS.items()
}

now = datetime.now(timezone.utc)

audit_freshness = {
    name: evaluate_freshness(
        name,
        doc,
        now,
    )
    for name, doc in audit_results.items()
}

critical = []
warnings = []
missing = []

effective_statuses = {}

for name, doc in audit_results.items():

    raw_status = str(
        doc.get(
            "status",
            "missing",
        )
    ).lower()

    freshness = audit_freshness[name]
    freshness_status = freshness["status"]

    effective_status = raw_status

    #
    # Freshness is fail-closed and can only worsen
    # an audit's effective status.
    #
    if freshness_status == "critical":
        effective_status = "critical"

    elif (
        freshness_status == "warning"
        and raw_status == "ok"
    ):
        effective_status = "warning"

    effective_statuses[name] = (
        effective_status
    )

    if raw_status == "missing":
        missing.append(name)

        critical.append({
            "audit": name,
            "status": "missing",
            "effective_status": "critical",
            "detail": "Audit file missing.",
            "path": str(AUDITS[name]),
            "freshness": freshness,
        })

        continue

    if raw_status in {"critical", "error"}:
        critical.append({
            "audit": name,
            "status": raw_status,
            "effective_status": "critical",
            "failed_checks":
                doc.get("failed_checks", []),
            "freshness": freshness,
        })

        continue

    if raw_status in {"warning", "warn"}:
        warnings.append({
            "audit": name,
            "status": raw_status,
            "effective_status": "warning",
            "failed_checks":
                doc.get("failed_checks", []),
            "freshness": freshness,
        })

        continue

    if raw_status != "ok":
        warnings.append({
            "audit": name,
            "status": raw_status,
            "effective_status": "warning",
            "detail":
                "Unexpected audit status.",
            "freshness": freshness,
        })

        continue

    #
    # Raw audit is healthy.
    # Freshness can still downgrade it.
    #
    if freshness_status == "critical":
        critical.append({
            "audit": name,
            "status": raw_status,
            "effective_status": "critical",
            "detail":
                "Audit output failed freshness policy.",
            "freshness": freshness,
        })

    elif freshness_status == "warning":
        warnings.append({
            "audit": name,
            "status": raw_status,
            "effective_status": "warning",
            "detail":
                "Audit output is approaching stale limit.",
            "freshness": freshness,
        })


go_nogo = (
    "GO_FOR_CONTINUED_PREPROD_OBSERVATION"
)

if critical:
    go_nogo = (
        "NO_GO_FIX_CRITICALS_FIRST"
    )

elif warnings:
    go_nogo = (
        "GO_WITH_WARNINGS"
    )


summary = {
    "audits_total": len(AUDITS),

    "audits_ok": sum(
        1
        for status in effective_statuses.values()
        if status == "ok"
    ),

    "audits_warning": len(warnings),

    "audits_critical": len(critical),

    "audits_missing": len(missing),

    "freshness_ok": sum(
        1
        for item in audit_freshness.values()
        if item["status"] == "ok"
    ),

    "freshness_warning": sum(
        1
        for item in audit_freshness.values()
        if item["status"] == "warning"
    ),

    "freshness_critical": sum(
        1
        for item in audit_freshness.values()
        if item["status"] == "critical"
    ),

    "go_nogo": go_nogo,
}


result = {
    "generated_at": utc_now(),

    "status": (
        "ok"
        if not critical
        else "critical"
    ),

    "engine":
        "preprod_go_nogo_master_audit_v2",

    "freshness_policy": {
        "timestamp_authority":
            "document_timestamp",

        "filesystem_mtime_authoritative":
            False,

        "future_tolerance_seconds":
            FUTURE_TOLERANCE_SECONDS,

        "thresholds_seconds":
            FRESHNESS_POLICY_SECONDS,
    },

    "summary": summary,

    "audit_statuses": {
        name: doc.get("status")
        for name, doc in audit_results.items()
    },

    "effective_audit_statuses":
        effective_statuses,

    "audit_freshness":
        audit_freshness,

    "critical_items":
        critical,

    "warning_items":
        warnings,

    "recommendation": (
        "Continue production-like PREPROD observation."
        if not critical
        else
        "Fix critical items before starting or extending "
        "production-like PREPROD."
    ),
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
            "status":
                result["status"],

            "summary":
                summary,

            "audit_statuses":
                result["audit_statuses"],

            "effective_audit_statuses":
                effective_statuses,

            "audit_freshness":
                audit_freshness,

            "critical_items":
                critical,

            "warning_items":
                warnings,
        },
        indent=2,
        ensure_ascii=False,
    )
)
