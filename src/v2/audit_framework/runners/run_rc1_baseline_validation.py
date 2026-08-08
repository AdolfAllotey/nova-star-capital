from __future__ import annotations

from pathlib import Path
import sys

from src.v2.audit_framework.core.constants import (
    FRAMEWORK_HISTORY_PATH,
    FRAMEWORK_REGISTRY_PATH,
)
from src.v2.audit_framework.core.utils import (
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    read_json,
    utc_now_iso,
)
from src.v2.audit_framework.validators import (
    RC1BaselineValidator,
)


def build_markdown(
    payload: dict,
) -> str:
    summary = payload["summary"]

    lines = [
        "# RC1 Baseline Validation Report",
        "",
        f"- Audit ID: `{payload['audit_id']}`",
        f"- Baseline ID: `{payload['baseline_id']}`",
        f"- Release: `{payload['release']}`",
        f"- Status: `{payload['status']}`",
        f"- Passed checks: `{summary['passed']}`",
        f"- Warnings: `{summary['warnings']}`",
        (
            "- Blocking failures: "
            f"`{summary['blocking_failures']}`"
        ),
        (
            "- Total checks: "
            f"`{summary['total_checks']}`"
        ),
        (
            "- RC1 aggregate SHA-256: "
            f"`{summary['aggregate_sha256']}`"
        ),
        (
            "- Package integrity SHA-256: "
            f"`{summary['package_integrity_sha256']}`"
        ),
        "- Provider executed: `false`",
        "- Automatic remediation: `false`",
        "",
        "## Validation checks",
        "",
    ]

    for check in payload["checks"]:
        lines.extend(
            [
                (
                    f"### {check['check_id']}"
                ),
                "",
                (
                    f"- Domain: `{check['domain']}`"
                ),
                (
                    f"- Status: `{check['status']}`"
                ),
                (
                    "- Blocking: "
                    f"`{str(check['blocking']).lower()}`"
                ),
                (
                    f"- Message: {check['message']}"
                ),
                (
                    f"- Expected: `{check['expected']}`"
                ),
                (
                    f"- Observed: `{check['observed']}`"
                ),
                "",
            ]
        )

    return "\n".join(lines)


def main() -> int:
    registry = read_json(
        FRAMEWORK_REGISTRY_PATH
    )

    latest = registry.get(
        "latest_collection"
    )

    if not isinstance(
        latest,
        dict,
    ):
        raise RuntimeError(
            "No latest artifact collection "
            "registered."
        )

    package_dir = Path(
        latest["package_dir"]
    )

    validator = RC1BaselineValidator(
        package_dir=package_dir
    )

    result = validator.validate()

    payload = result.to_dict()

    json_path = (
        package_dir
        / "baseline_validation_report.json"
    )

    markdown_path = (
        package_dir
        / "BASELINE_VALIDATION_REPORT.md"
    )

    atomic_write_json(
        json_path,
        payload,
    )

    atomic_write_text(
        markdown_path,
        build_markdown(payload),
    )

    registry["updated_at"] = (
        utc_now_iso()
    )

    registry["capabilities"][
        "baseline_validation"
    ] = "READY"

    registry["latest_validation"] = {
        "audit_id": payload["audit_id"],
        "baseline_id": (
            payload["baseline_id"]
        ),
        "status": payload["status"],
        "package_dir": str(
            package_dir
        ),
        "report_path": str(
            json_path
        ),
        "passed": payload["summary"][
            "passed"
        ],
        "warnings": payload["summary"][
            "warnings"
        ],
        "blocking_failures": (
            payload["summary"][
                "blocking_failures"
            ]
        ),
        "provider_executed": False,
    }

    registry["next_phase"] = {
        "name": (
            "AUDIT_PACKAGE_BUILDER"
        ),
        "objective": (
            "Build the complete provider-"
            "independent RC1 audit package, "
            "manifest and audit instructions."
        ),
    }

    atomic_write_json(
        FRAMEWORK_REGISTRY_PATH,
        registry,
    )

    append_jsonl(
        FRAMEWORK_HISTORY_PATH,
        {
            "event": (
                "RC1_BASELINE_VALIDATION_COMPLETED"
            ),
            "timestamp": utc_now_iso(),
            "audit_id": payload["audit_id"],
            "baseline_id": (
                payload["baseline_id"]
            ),
            "status": payload["status"],
            "passed": payload["summary"][
                "passed"
            ],
            "warnings": payload["summary"][
                "warnings"
            ],
            "blocking_failures": (
                payload["summary"][
                    "blocking_failures"
                ]
            ),
            "provider_executed": False,
            "automatic_remediation": False,
        },
    )

    print(
        "===== RC1 BASELINE VALIDATION COMPLETE ====="
    )
    print(
        f"Audit ID: {payload['audit_id']}"
    )
    print(
        f"Baseline ID: {payload['baseline_id']}"
    )
    print(
        f"Status: {payload['status']}"
    )
    print(
        "Passed checks: "
        f"{payload['summary']['passed']}"
    )
    print(
        "Warnings: "
        f"{payload['summary']['warnings']}"
    )
    print(
        "Blocking failures: "
        f"{payload['summary']['blocking_failures']}"
    )
    print(
        "Total checks: "
        f"{payload['summary']['total_checks']}"
    )
    print(
        "RC1 aggregate SHA256: "
        f"{payload['summary']['aggregate_sha256']}"
    )
    print(
        "Package integrity SHA256: "
        f"{payload['summary']['package_integrity_sha256']}"
    )
    print(
        "Provider executed: false"
    )
    print(
        "Automatic remediation: false"
    )
    print(
        "Next phase: AUDIT_PACKAGE_BUILDER"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "RC1 BASELINE VALIDATION "
            f"FAILED: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
