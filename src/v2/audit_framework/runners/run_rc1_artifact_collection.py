from __future__ import annotations

from pathlib import Path
import json
import sys

from src.v2.audit_framework.collectors import (
    InstitutionalArtifactCollector,
    build_rc1_artifact_definitions,
)
from src.v2.audit_framework.core.constants import (
    APP_DIR,
    AUDIT_FRAMEWORK_SCHEMA_VERSION,
    AUDIT_FRAMEWORK_VERSION,
    FRAMEWORK_HISTORY_PATH,
    FRAMEWORK_REGISTRY_PATH,
    PACKAGES_DIR,
    RC1_CURRENT_BASELINE_PATH,
    RC1_RELEASE_GATE_PATH,
)
from src.v2.audit_framework.core.enums import (
    AuditProvider,
    AuditStatus,
    AuditType,
)
from src.v2.audit_framework.core.models import (
    AuditRequest,
    AuditTarget,
)
from src.v2.audit_framework.core.utils import (
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    build_timestamp,
    read_json,
    sha256_file,
    utc_now_iso,
)


def first_non_empty(
    payload: dict,
    keys: tuple[str, ...],
    default: str,
) -> str:
    for key in keys:
        value = payload.get(key)

        if value not in (
            None,
            "",
        ):
            return str(value)

    return default


def build_target() -> AuditTarget:
    release_gate = read_json(
        RC1_RELEASE_GATE_PATH
    )

    baseline = read_json(
        RC1_CURRENT_BASELINE_PATH
    )

    baseline_id = first_non_empty(
        baseline,
        (
            "baseline_id",
            "id",
            "release_baseline_id",
        ),
        "UNKNOWN",
    )

    baseline_status = first_non_empty(
        baseline,
        (
            "status",
            "baseline_status",
            "state",
        ),
        first_non_empty(
            release_gate,
            (
                "baseline_status",
                "status",
            ),
            "UNKNOWN",
        ),
    )

    aggregate_sha256 = None

    for payload in (
        baseline,
        release_gate,
    ):
        for key in (
            "aggregate_sha256",
            "baseline_aggregate_sha256",
            "sha256",
        ):
            value = payload.get(key)

            if isinstance(value, str):
                aggregate_sha256 = value
                break

        if aggregate_sha256:
            break

    return AuditTarget(
        project="Nova Star Capital",
        release="RC1",
        baseline_id=baseline_id,
        baseline_status=(
            baseline_status
        ),
        aggregate_sha256=(
            aggregate_sha256
        ),
        source_root=str(APP_DIR),
    )


def build_markdown_report(
    payload: dict,
) -> str:
    summary = payload["summary"]

    lines = [
        "# RC1 Artifact Collection Report",
        "",
        f"- Audit ID: `{payload['audit_id']}`",
        f"- Status: `{payload['status']}`",
        (
            "- Required artifacts: "
            f"`{summary['required_collected']}/"
            f"{summary['required_expected']}`"
        ),
        (
            "- Optional artifacts collected: "
            f"`{summary['optional_collected']}`"
        ),
        (
            "- Total files collected: "
            f"`{summary['total_collected']}`"
        ),
        (
            "- Aggregate SHA-256: "
            f"`{summary['aggregate_sha256']}`"
        ),
        (
            "- Source mutation detected: "
            f"`{str(summary['source_mutation_detected']).lower()}`"
        ),
        "- Provider executed: `false`",
        "",
        "## Collected artifacts",
        "",
    ]

    for artifact in payload["artifacts"]:
        lines.extend(
            [
                (
                    f"### {artifact['artifact_id']}"
                ),
                "",
                (
                    f"- Role: `{artifact['role']}`"
                ),
                (
                    "- Required: "
                    f"`{str(artifact['required']).lower()}`"
                ),
                (
                    f"- Source: `{artifact['source_path']}`"
                ),
                (
                    f"- Package: `{artifact['package_path']}`"
                ),
                (
                    f"- Size: `{artifact['size_bytes']}` bytes"
                ),
                (
                    f"- SHA-256: `{artifact['sha256']}`"
                ),
                "",
            ]
        )

    if payload["issues"]:
        lines.extend(
            [
                "## Collection observations",
                "",
            ]
        )

        for issue in payload["issues"]:
            lines.append(
                "- "
                f"`{issue['issue_type']}` — "
                f"{issue['artifact_id']}: "
                f"{issue['message']}"
            )

        lines.append("")

    return "\n".join(lines)


def update_registry(
    audit_id: str,
    package_dir: Path,
    report_payload: dict,
) -> None:
    registry = read_json(
        FRAMEWORK_REGISTRY_PATH
    )

    registry["updated_at"] = (
        utc_now_iso()
    )

    registry["capabilities"][
        "artifact_collection"
    ] = "READY"

    registry["latest_collection"] = {
        "audit_id": audit_id,
        "status": report_payload[
            "status"
        ],
        "package_dir": str(
            package_dir
        ),
        "aggregate_sha256": (
            report_payload["summary"][
                "aggregate_sha256"
            ]
        ),
        "total_collected": (
            report_payload["summary"][
                "total_collected"
            ]
        ),
        "provider_executed": False,
    }

    registry["next_phase"] = {
        "name": "BASELINE_VALIDATOR",
        "objective": (
            "Validate the integrity and semantic "
            "consistency of the frozen RC1 "
            "baseline and collected artifacts."
        ),
    }

    atomic_write_json(
        FRAMEWORK_REGISTRY_PATH,
        registry,
    )


def main() -> int:
    timestamp = build_timestamp()

    audit_id = (
        f"RC1-ENGINEERING-AUDIT-"
        f"{timestamp}"
    )

    package_dir = (
        PACKAGES_DIR
        / audit_id
    )

    request = AuditRequest(
        audit_id=audit_id,
        audit_type=(
            AuditType.BASELINE_ENGINEERING
        ),
        provider=AuditProvider.NONE,
        status=AuditStatus.COLLECTING,
        target=build_target(),
        created_at=utc_now_iso(),
        objectives=[
            (
                "Prepare a reproducible RC1 "
                "engineering audit package."
            ),
            (
                "Collect certified release, "
                "baseline, Master, governance "
                "and certification artifacts."
            ),
        ],
        constraints=[
            (
                "Do not modify the RC1 baseline."
            ),
            (
                "Do not execute an audit provider."
            ),
            (
                "Verify every copy using SHA-256."
            ),
            (
                "Separate audit from remediation."
            ),
        ],
        requested_deliverables=[
            "Artifact inventory",
            "Collection report",
            "Checksum inventory",
            "RC1 audit package",
        ],
        metadata={
            "framework_version": (
                AUDIT_FRAMEWORK_VERSION
            ),
            "schema_version": (
                AUDIT_FRAMEWORK_SCHEMA_VERSION
            ),
            "phase": (
                "ARTIFACT_COLLECTION"
            ),
        },
    )

    collector = (
        InstitutionalArtifactCollector(
            build_rc1_artifact_definitions()
        )
    )

    result = collector.collect(
        request=request,
        package_dir=package_dir,
    )

    payload = result.to_dict()

    atomic_write_json(
        package_dir
        / "audit_request.json",
        request.to_dict(),
    )

    atomic_write_json(
        package_dir
        / "artifact_collection_report.json",
        payload,
    )

    atomic_write_json(
        package_dir
        / "artifact_inventory.json",
        {
            "schema_version": "1.0",
            "audit_id": audit_id,
            "aggregate_sha256": (
                payload["summary"][
                    "aggregate_sha256"
                ]
            ),
            "artifact_count": (
                payload["summary"][
                    "total_collected"
                ]
            ),
            "artifacts": payload[
                "artifacts"
            ],
        },
    )

    atomic_write_text(
        package_dir
        / "ARTIFACT_COLLECTION_REPORT.md",
        build_markdown_report(
            payload
        ),
    )

    update_registry(
        audit_id=audit_id,
        package_dir=package_dir,
        report_payload=payload,
    )

    append_jsonl(
        FRAMEWORK_HISTORY_PATH,
        {
            "event": (
                "RC1_ARTIFACT_COLLECTION_COMPLETED"
            ),
            "timestamp": utc_now_iso(),
            "audit_id": audit_id,
            "status": payload["status"],
            "package_dir": str(
                package_dir
            ),
            "artifact_count": (
                payload["summary"][
                    "total_collected"
                ]
            ),
            "aggregate_sha256": (
                payload["summary"][
                    "aggregate_sha256"
                ]
            ),
            "provider_executed": False,
            "source_mutation_detected": (
                payload["summary"][
                    "source_mutation_detected"
                ]
            ),
        },
    )

    print(
        "===== RC1 ARTIFACT COLLECTION COMPLETE ====="
    )
    print(
        f"Audit ID: {audit_id}"
    )
    print(
        f"Status: {payload['status']}"
    )
    print(
        f"Package: {package_dir}"
    )
    print(
        "Required artifacts: "
        f"{payload['summary']['required_collected']}/"
        f"{payload['summary']['required_expected']}"
    )
    print(
        "Optional artifacts collected: "
        f"{payload['summary']['optional_collected']}"
    )
    print(
        "Total files collected: "
        f"{payload['summary']['total_collected']}"
    )
    print(
        "Aggregate SHA256: "
        f"{payload['summary']['aggregate_sha256']}"
    )
    print(
        "Source mutation detected: false"
    )
    print(
        "Provider executed: false"
    )
    print(
        "Next phase: BASELINE_VALIDATOR"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "RC1 ARTIFACT COLLECTION "
            f"FAILED: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
