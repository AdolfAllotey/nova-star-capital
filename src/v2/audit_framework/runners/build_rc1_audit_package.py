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
    read_json,
    utc_now_iso,
)
from src.v2.audit_framework.manifests.audit_package_builder import (
    RC1AuditPackageBuilder,
)


def main() -> int:
    registry = read_json(
        FRAMEWORK_REGISTRY_PATH
    )

    latest_validation = registry.get(
        "latest_validation"
    )

    if not isinstance(
        latest_validation,
        dict,
    ):
        raise RuntimeError(
            "No validated RC1 package registered."
        )

    if (
        latest_validation.get(
            "status"
        )
        != "PASS"
    ):
        raise RuntimeError(
            "Latest baseline validation "
            "is not PASS."
        )

    package_dir = Path(
        latest_validation[
            "package_dir"
        ]
    )

    previous_package = registry.get(
        "latest_audit_package"
    )

    if not isinstance(
        previous_package,
        dict,
    ):
        previous_package = {}

    previous_audit_id = (
        previous_package.get("audit_id")
    )

    previous_package_sha256 = (
        previous_package.get(
            "package_readiness_sha256"
        )
    )

    builder = RC1AuditPackageBuilder(
        package_dir=package_dir
    )

    manifest = builder.build()

    deterministic_rebuild = bool(
        previous_audit_id
        == manifest.audit_id
        and previous_package_sha256
        == manifest.package_readiness_sha256
    )

    manifest_payload = (
        manifest.to_dict()
    )

    registry["updated_at"] = (
        utc_now_iso()
    )

    registry["capabilities"][
        "audit_package_builder"
    ] = "READY"

    registry["latest_audit_package"] = {
        "audit_id": (
            manifest.audit_id
        ),
        "release": (
            manifest.release
        ),
        "baseline_id": (
            manifest.baseline_id
        ),
        "status": (
            manifest.package_status
        ),
        "package_dir": str(
            package_dir
        ),
        "manifest_path": str(
            package_dir
            / "AUDIT_PACKAGE_MANIFEST.json"
        ),
        "package_readiness_sha256": (
            manifest.package_readiness_sha256
        ),
        "file_count": len(
            manifest.files
        ),
        "provider": "NONE",
        "provider_executed": False,
        "automatic_remediation": False,
        "deterministic_rebuild": (
            deterministic_rebuild
        ),
        "previous_package_readiness_sha256": (
            previous_package_sha256
        ),
    }

    registry["next_phase"] = {
        "name": "PROVIDER_ADAPTER",
        "objective": (
            "Implement the first provider adapter "
            "and prepare controlled Codex audit "
            "execution without allowing automatic "
            "remediation."
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
                "RC1_AUDIT_PACKAGE_READY"
            ),
            "timestamp": utc_now_iso(),
            "audit_id": (
                manifest.audit_id
            ),
            "release": (
                manifest.release
            ),
            "baseline_id": (
                manifest.baseline_id
            ),
            "package_status": (
                manifest.package_status
            ),
            "package_dir": str(
                package_dir
            ),
            "package_readiness_sha256": (
                manifest.package_readiness_sha256
            ),
            "file_count": len(
                manifest.files
            ),
            "provider": "NONE",
            "provider_executed": False,
            "automatic_remediation": False,
            "deterministic_rebuild": (
                deterministic_rebuild
            ),
            "previous_package_readiness_sha256": (
                previous_package_sha256
            ),
        },
    )

    append_jsonl(
        FRAMEWORK_HISTORY_PATH,
        {
            "event": (
                "RC1_AUDIT_PACKAGE_VERIFIED"
            ),
            "timestamp": utc_now_iso(),
            "audit_id": manifest.audit_id,
            "package_readiness_sha256": (
                manifest.package_readiness_sha256
            ),
            "previous_package_readiness_sha256": (
                previous_package_sha256
            ),
            "deterministic_rebuild": (
                deterministic_rebuild
            ),
            "provider_executed": False,
            "automatic_remediation": False,
        },
    )

    print(
        "===== RC1 AUDIT PACKAGE READY ====="
    )
    print(
        f"Audit ID: {manifest.audit_id}"
    )
    print(
        f"Release: {manifest.release}"
    )
    print(
        f"Baseline ID: {manifest.baseline_id}"
    )
    print(
        f"Status: {manifest.package_status}"
    )
    print(
        f"Package: {package_dir}"
    )
    print(
        "Package files: "
        f"{len(manifest.files)}"
    )
    print(
        "Baseline aggregate SHA256: "
        f"{manifest.baseline_aggregate_sha256}"
    )
    print(
        "Collection aggregate SHA256: "
        f"{manifest.collection_aggregate_sha256}"
    )
    print(
        "Package readiness SHA256: "
        f"{manifest.package_readiness_sha256}"
    )
    print(
        "Deterministic rebuild: "
        f"{str(deterministic_rebuild).lower()}"
    )
    print(
        "Previous package readiness SHA256: "
        f"{previous_package_sha256}"
    )
    print(
        "Provider: NONE"
    )
    print(
        "Provider executed: false"
    )
    print(
        "Automatic remediation: false"
    )
    print(
        "Next phase: PROVIDER_ADAPTER"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "RC1 AUDIT PACKAGE BUILD "
            f"FAILED: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
