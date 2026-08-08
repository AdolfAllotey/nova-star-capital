from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
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
from src.v2.audit_framework.gates.codex import (
    CodexExecutionGate,
)


def main() -> int:
    registry = read_json(
        FRAMEWORK_REGISTRY_PATH
    )

    preparation = registry.get(
        "latest_provider_preparation"
    )

    if not isinstance(
        preparation,
        dict,
    ):
        raise RuntimeError(
            "No provider preparation exists."
        )

    if (
        preparation.get("provider_id")
        != "OPENAI_CODEX"
    ):
        raise RuntimeError(
            "Latest provider is not Codex."
        )

    if (
        preparation.get("status")
        != "PREPARED_DRY_RUN"
    ):
        raise RuntimeError(
            "Codex provider is not prepared."
        )

    if (
        preparation.get(
            "provider_executed"
        )
        is not False
    ):
        raise RuntimeError(
            "Provider execution already exists."
        )

    package_dir = Path(
        registry[
            "latest_audit_package"
        ][
            "package_dir"
        ]
    )

    gate = CodexExecutionGate(
        package_dir=package_dir
    )

    requested_by = os.environ.get(
        "NSC_GATE_REQUESTED_BY",
        "NSC_OPERATOR",
    )

    approved_by = os.environ.get(
        "NSC_GATE_APPROVED_BY",
        "ADOLF_ALLOTEY",
    )

    expires_at = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            hours=24
        )
    ).isoformat()

    request = gate.create_request(
        requested_by=requested_by,
        expires_at=expires_at,
    )

    approval = gate.approve(
        gate_id=request.gate_id,
        approved_by=approved_by,
    )

    validation = gate.validate(
        gate_id=request.gate_id
    )

    if (
        validation.status
        != "AUTHORIZED_FOR_SINGLE_EXECUTION"
    ):
        raise RuntimeError(
            "Codex execution gate validation "
            "did not authorize execution."
        )

    registry["updated_at"] = (
        utc_now_iso()
    )

    registry["capabilities"][
        "codex_execution_gate"
    ] = "READY"

    registry[
        "latest_execution_gate"
    ] = {
        "gate_id": request.gate_id,
        "provider_id": (
            request.provider_id
        ),
        "audit_id": request.audit_id,
        "status": validation.status,
        "requested_at": (
            request.requested_at
        ),
        "requested_by": (
            request.requested_by
        ),
        "approved_at": (
            approval.approved_at
        ),
        "approved_by": (
            approval.approved_by
        ),
        "expires_at": (
            request.expires_at
        ),
        "package_readiness_sha256": (
            request.package_readiness_sha256
        ),
        "payload_sha256": (
            request.payload_sha256
        ),
        "single_use": True,
        "consumed": False,
        "revoked": False,
        "provider_executed": False,
        "automatic_remediation": False,
        "human_approval": True,
        "execution_available": False,
        "gate_dir": str(
            gate.gate_root
            / request.gate_id
        ),
    }

    registry["active_providers"] = []

    registry["next_phase"] = {
        "name": "CODEX_ADAPTER",
        "objective": (
            "Implement the controlled Codex "
            "invocation adapter and execution "
            "receipt contract without enabling "
            "automatic remediation."
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
                "CODEX_EXECUTION_GATE_AUTHORIZED"
            ),
            "timestamp": utc_now_iso(),
            "gate_id": request.gate_id,
            "provider_id": (
                request.provider_id
            ),
            "audit_id": request.audit_id,
            "status": validation.status,
            "requested_by": (
                request.requested_by
            ),
            "approved_by": (
                approval.approved_by
            ),
            "expires_at": (
                request.expires_at
            ),
            "package_readiness_sha256": (
                request.package_readiness_sha256
            ),
            "payload_sha256": (
                request.payload_sha256
            ),
            "single_use": True,
            "consumed": False,
            "revoked": False,
            "provider_executed": False,
            "automatic_remediation": False,
            "execution_available": False,
        },
    )

    print(
        "===== CODEX EXECUTION GATE AUTHORIZED ====="
    )

    print(
        "Gate ID:",
        request.gate_id,
    )

    print(
        "Provider:",
        request.provider_id,
    )

    print(
        "Audit ID:",
        request.audit_id,
    )

    print(
        "Status:",
        validation.status,
    )

    print(
        "Requested by:",
        request.requested_by,
    )

    print(
        "Approved by:",
        approval.approved_by,
    )

    print(
        "Expires at:",
        request.expires_at,
    )

    print(
        "Package readiness SHA256:",
        request.package_readiness_sha256,
    )

    print(
        "Payload SHA256:",
        request.payload_sha256,
    )

    print(
        "Checks:",
        len(validation.checks),
    )

    print(
        "Blocking failures:",
        validation.blocking_failures,
    )

    print(
        "Warnings:",
        validation.warnings,
    )

    print(
        "Single use: true"
    )

    print(
        "Consumed: false"
    )

    print(
        "Revoked: false"
    )

    print(
        "Provider executed: false"
    )

    print(
        "Automatic remediation: false"
    )

    print(
        "Execution available: false"
    )

    print(
        "Active providers: 0"
    )

    print(
        "Next phase: CODEX_ADAPTER"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            "CODEX EXECUTION GATE FAILED: "
            f"{exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
