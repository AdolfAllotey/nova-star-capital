from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sys

from src.v2.audit_framework.core.constants import (
    APP_DIR,
    AUDIT_DATA_DIR,
    AUDIT_FRAMEWORK_NAME,
    AUDIT_FRAMEWORK_SCHEMA_VERSION,
    AUDIT_FRAMEWORK_VERSION,
    FRAMEWORK_HISTORY_PATH,
    FRAMEWORK_REGISTRY_PATH,
    MANIFESTS_DIR,
    PACKAGES_DIR,
    REGISTRY_DIR,
    REPORTS_DIR,
    TEMP_DIR,
)
from src.v2.audit_framework.core.utils import (
    append_jsonl,
    atomic_write_json,
    sha256_file,
    utc_now_iso,
)


FRAMEWORK_ROOT = (
    APP_DIR
    / "src"
    / "v2"
    / "audit_framework"
)


REQUIRED_DIRECTORIES = [
    "core",
    "collectors",
    "validators",
    "manifests",
    "providers",
    "reports",
    "schemas",
    "runners",
    "tests",
]


REQUIRED_FILES = [
    "__init__.py",
    "core/constants.py",
    "core/enums.py",
    "core/exceptions.py",
    "core/utils.py",
    "core/models.py",
    "core/interfaces.py",
    "core/context.py",
    "schemas/audit_package.schema.json",
    "schemas/audit_report.schema.json",
    "schemas/recommendation.schema.json",
]


def validate_json_file(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(
            f"Missing JSON schema: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON schema {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Schema is not an object: {path}"
        )

    if payload.get("type") != "object":
        raise RuntimeError(
            f"Schema root type is not object: {path}"
        )

    return payload


def validate_foundation() -> dict[str, Any]:
    missing_directories = [
        item
        for item in REQUIRED_DIRECTORIES
        if not (
            FRAMEWORK_ROOT / item
        ).is_dir()
    ]

    missing_files = [
        item
        for item in REQUIRED_FILES
        if not (
            FRAMEWORK_ROOT / item
        ).is_file()
    ]

    if missing_directories:
        raise RuntimeError(
            "Missing framework directories: "
            + ", ".join(
                missing_directories
            )
        )

    if missing_files:
        raise RuntimeError(
            "Missing framework files: "
            + ", ".join(
                missing_files
            )
        )

    schema_paths = [
        FRAMEWORK_ROOT
        / "schemas"
        / "audit_package.schema.json",
        FRAMEWORK_ROOT
        / "schemas"
        / "audit_report.schema.json",
        FRAMEWORK_ROOT
        / "schemas"
        / "recommendation.schema.json",
    ]

    schemas: list[dict[str, Any]] = []

    for schema_path in schema_paths:
        payload = validate_json_file(
            schema_path
        )

        schemas.append(
            {
                "path": str(schema_path),
                "title": payload.get(
                    "title"
                ),
                "schema_id": payload.get(
                    "$id"
                ),
                "sha256": sha256_file(
                    schema_path
                ),
            }
        )

    return {
        "status": "PASS",
        "missing_directories": [],
        "missing_files": [],
        "schemas": schemas,
    }


def main() -> int:
    created_at = utc_now_iso()

    for path in (
        AUDIT_DATA_DIR,
        PACKAGES_DIR,
        REPORTS_DIR,
        MANIFESTS_DIR,
        REGISTRY_DIR,
        TEMP_DIR,
    ):
        path.mkdir(
            parents=True,
            exist_ok=True,
        )

    validation = validate_foundation()

    registry = {
        "schema_version": (
            AUDIT_FRAMEWORK_SCHEMA_VERSION
        ),
        "framework": (
            AUDIT_FRAMEWORK_NAME
        ),
        "framework_version": (
            AUDIT_FRAMEWORK_VERSION
        ),
        "status": "FOUNDATION_READY",
        "created_at": created_at,
        "updated_at": created_at,
        "source_root": str(
            FRAMEWORK_ROOT
        ),
        "data_root": str(
            AUDIT_DATA_DIR
        ),
        "principles": [
            "PROVIDER_INDEPENDENT",
            "BASELINE_IMMUTABLE",
            "AUDIT_BEFORE_CORRECTION",
            "HUMAN_VALIDATION_REQUIRED",
            "NO_AUTOMATIC_CODE_CHANGE",
            "FULL_TRACEABILITY",
            "SCHEMA_DRIVEN",
        ],
        "capabilities": {
            "foundation": "READY",
            "artifact_collection": (
                "NOT_IMPLEMENTED"
            ),
            "baseline_validation": (
                "NOT_IMPLEMENTED"
            ),
            "manifest_building": (
                "NOT_IMPLEMENTED"
            ),
            "provider_routing": (
                "NOT_IMPLEMENTED"
            ),
            "report_normalization": (
                "NOT_IMPLEMENTED"
            ),
            "recommendation_engine": (
                "NOT_IMPLEMENTED"
            ),
            "engineering_scoring": (
                "MODEL_READY"
            ),
        },
        "active_providers": [],
        "schemas": validation["schemas"],
        "validation": validation,
        "next_phase": {
            "name": (
                "ARTIFACT_COLLECTOR"
            ),
            "objective": (
                "Collect RC1 release, baseline, "
                "governance and certification "
                "artifacts without modifying them."
            ),
        },
    }

    atomic_write_json(
        FRAMEWORK_REGISTRY_PATH,
        registry,
    )

    append_jsonl(
        FRAMEWORK_HISTORY_PATH,
        {
            "event": (
                "AUDIT_FRAMEWORK_FOUNDATION_INITIALIZED"
            ),
            "timestamp": created_at,
            "framework_version": (
                AUDIT_FRAMEWORK_VERSION
            ),
            "status": "FOUNDATION_READY",
            "registry_path": str(
                FRAMEWORK_REGISTRY_PATH
            ),
        },
    )

    print(
        "===== AUDIT FRAMEWORK FOUNDATION READY ====="
    )
    print(
        f"Framework: {AUDIT_FRAMEWORK_NAME}"
    )
    print(
        f"Version: {AUDIT_FRAMEWORK_VERSION}"
    )
    print(
        "Status: FOUNDATION_READY"
    )
    print(
        f"Source root: {FRAMEWORK_ROOT}"
    )
    print(
        f"Data root: {AUDIT_DATA_DIR}"
    )
    print(
        f"Registry: {FRAMEWORK_REGISTRY_PATH}"
    )
    print(
        f"History: {FRAMEWORK_HISTORY_PATH}"
    )
    print(
        "Active providers: none"
    )
    print(
        "RC1 baseline modified: false"
    )
    print(
        "Next phase: ARTIFACT_COLLECTOR"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "AUDIT FRAMEWORK FOUNDATION "
            f"FAILED: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
