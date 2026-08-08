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
from src.v2.audit_framework.providers.codex import (
    CodexAuditAdapter,
)


def main() -> int:
    registry = read_json(
        FRAMEWORK_REGISTRY_PATH
    )

    latest_package = registry.get(
        "latest_audit_package"
    )

    if not isinstance(
        latest_package,
        dict,
    ):
        raise RuntimeError(
            "No audit package is registered."
        )

    if (
        latest_package.get(
            "status"
        )
        != "READY_FOR_PROVIDER_AUDIT"
    ):
        raise RuntimeError(
            "Audit package is not ready."
        )

    if (
        latest_package.get(
            "deterministic_rebuild"
        )
        is not True
    ):
        raise RuntimeError(
            "Package determinism is not validated."
        )

    if registry.get(
        "active_providers"
    ):
        raise RuntimeError(
            "An active provider is already registered."
        )

    package_dir = Path(
        latest_package[
            "package_dir"
        ]
    )

    adapter = CodexAuditAdapter()

    result = adapter.prepare(
        package_dir
    )

    registry["updated_at"] = (
        utc_now_iso()
    )

    registry["capabilities"][
        "provider_adapter"
    ] = "READY"

    registry["capabilities"][
        "codex_provider_adapter"
    ] = "READY"

    available_providers = (
        registry.setdefault(
            "available_providers",
            {},
        )
    )

    available_providers[
        adapter.PROVIDER_ID
    ] = adapter.capabilities.to_dict()

    registry[
        "latest_provider_preparation"
    ] = {
        "provider_id": (
            result.provider_id
        ),
        "audit_id": result.audit_id,
        "status": result.status,
        "execution_mode": (
            result.execution_mode
        ),
        "prepared_at": (
            result.prepared_at
        ),
        "payload_path": (
            result.payload_path
        ),
        "payload_sha256": (
            result.payload_sha256
        ),
        "package_readiness_sha256": (
            result.package_readiness_sha256
        ),
        "blocking_failures": (
            result.blocking_failures
        ),
        "warnings": result.warnings,
        "provider_executed": False,
        "automatic_remediation": False,
        "human_approval_required": True,
    }

    registry["active_providers"] = []

    registry["next_phase"] = {
        "name": (
            "CODEX_EXECUTION_GATE"
        ),
        "objective": (
            "Validate the explicit human approval "
            "gate and controlled execution contract "
            "before any Codex audit invocation."
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
                "CODEX_PROVIDER_PREPARED"
            ),
            "timestamp": utc_now_iso(),
            "provider_id": (
                result.provider_id
            ),
            "audit_id": result.audit_id,
            "status": result.status,
            "execution_mode": (
                result.execution_mode
            ),
            "payload_path": (
                result.payload_path
            ),
            "payload_sha256": (
                result.payload_sha256
            ),
            "package_readiness_sha256": (
                result.package_readiness_sha256
            ),
            "blocking_failures": (
                result.blocking_failures
            ),
            "warnings": result.warnings,
            "provider_executed": False,
            "automatic_remediation": False,
            "human_approval_required": True,
        },
    )

    print(
        "===== CODEX PROVIDER PREPARED ====="
    )

    print(
        "Provider ID:",
        result.provider_id,
    )

    print(
        "Audit ID:",
        result.audit_id,
    )

    print(
        "Status:",
        result.status,
    )

    print(
        "Execution mode:",
        result.execution_mode,
    )

    print(
        "Payload:",
        result.payload_path,
    )

    print(
        "Payload SHA256:",
        result.payload_sha256,
    )

    print(
        "Package readiness SHA256:",
        result.package_readiness_sha256,
    )

    print(
        "Checks:",
        len(result.checks),
    )

    print(
        "Blocking failures:",
        result.blocking_failures,
    )

    print(
        "Warnings:",
        result.warnings,
    )

    print(
        "Provider executed: false"
    )

    print(
        "Automatic remediation: false"
    )

    print(
        "Active providers: 0"
    )

    print(
        "Human approval required: true"
    )

    print(
        "Next phase: CODEX_EXECUTION_GATE"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "CODEX PROVIDER PREPARATION FAILED: "
            f"{exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
