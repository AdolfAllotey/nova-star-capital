from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import uuid

from src.v2.audit_framework.core.utils import (
    atomic_write_json,
    read_json,
    sha256_file,
    utc_now_iso,
)
from src.v2.audit_framework.gates.contracts import (
    ExecutionGateApproval,
    ExecutionGateReceipt,
    ExecutionGateRequest,
    ExecutionGateValidation,
)


class CodexExecutionGate:
    PROVIDER_ID = "OPENAI_CODEX"

    GATE_VERSION = "1.0.0"

    APPROVAL_SCOPE = (
        "RC1_ENGINEERING_AUDIT_READ_ONLY"
    )

    EXECUTION_MODE = (
        "CONTROLLED_PROVIDER_AUDIT"
    )

    def __init__(
        self,
        *,
        package_dir: Path,
        gate_root: Path | None = None,
    ) -> None:
        self.package_dir = (
            package_dir.resolve()
        )

        self.payload_path = (
            self.package_dir
            / "provider_payloads"
            / "openai_codex"
            / "codex_audit_payload.json"
        )

        self.preparation_path = (
            self.package_dir
            / "provider_payloads"
            / "openai_codex"
            / "codex_preparation_report.json"
        )

        self.manifest_path = (
            self.package_dir
            / "AUDIT_PACKAGE_MANIFEST.json"
        )

        self.ready_path = (
            self.package_dir
            / "AUDIT_PACKAGE_READY.json"
        )

        self.gate_root = (
            gate_root.resolve()
            if gate_root
            else (
                self.package_dir
                / "execution_gates"
                / "openai_codex"
            )
        )

        self.gate_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _parse_datetime(
        value: str,
    ) -> datetime:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(
            timezone.utc
        )

    @staticmethod
    def _check(
        *,
        check_id: str,
        domain: str,
        condition: bool,
        message_pass: str,
        message_fail: str,
        blocking: bool = True,
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "check_id": check_id,
            "domain": domain,
            "status": (
                "PASS"
                if condition
                else "FAIL"
            ),
            "blocking": blocking,
            "message": (
                message_pass
                if condition
                else message_fail
            ),
            "evidence": evidence or [],
        }

    def _load_context(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ]:
        required_paths = (
            self.manifest_path,
            self.ready_path,
            self.payload_path,
            self.preparation_path,
        )

        missing = [
            str(path)
            for path in required_paths
            if not path.is_file()
        ]

        if missing:
            raise RuntimeError(
                "Missing execution-gate "
                "dependencies: "
                + ", ".join(missing)
            )

        manifest = read_json(
            self.manifest_path
        )

        ready = read_json(
            self.ready_path
        )

        payload = read_json(
            self.payload_path
        )

        preparation = read_json(
            self.preparation_path
        )

        return (
            manifest,
            ready,
            payload,
            preparation,
        )

    @staticmethod
    def _build_gate_id(
        *,
        audit_id: str,
        package_sha256: str,
        payload_sha256: str,
    ) -> str:
        random_part = uuid.uuid4().hex[
            :12
        ].upper()

        stable_seed = (
            f"{audit_id}|"
            f"{package_sha256}|"
            f"{payload_sha256}"
        )

        stable_part = hashlib.sha256(
            stable_seed.encode(
                "utf-8"
            )
        ).hexdigest()[:12].upper()

        return (
            "GATE-CODEX-"
            f"{stable_part}-"
            f"{random_part}"
        )

    def create_request(
        self,
        *,
        requested_by: str,
        expires_at: str,
    ) -> ExecutionGateRequest:
        (
            manifest,
            ready,
            payload,
            preparation,
        ) = self._load_context()

        expires = self._parse_datetime(
            expires_at
        )

        if expires <= self._now():
            raise ValueError(
                "Execution gate expiration "
                "must be in the future."
            )

        package_sha256 = manifest[
            "package_readiness_sha256"
        ]

        payload_sha256 = sha256_file(
            self.payload_path
        )

        if (
            payload_sha256
            != preparation[
                "payload_sha256"
            ]
        ):
            raise RuntimeError(
                "Prepared payload checksum "
                "does not match."
            )

        if (
            payload[
                "package_readiness_sha256"
            ]
            != package_sha256
        ):
            raise RuntimeError(
                "Payload is not bound to "
                "the current package."
            )

        if (
            ready["status"]
            != "READY_FOR_PROVIDER_AUDIT"
        ):
            raise RuntimeError(
                "Audit package is not ready."
            )

        gate_id = self._build_gate_id(
            audit_id=manifest["audit_id"],
            package_sha256=(
                package_sha256
            ),
            payload_sha256=(
                payload_sha256
            ),
        )

        request = ExecutionGateRequest(
            schema_version="1.0",
            gate_id=gate_id,
            provider_id=self.PROVIDER_ID,
            audit_id=manifest["audit_id"],
            release=manifest["release"],
            package_readiness_sha256=(
                package_sha256
            ),
            payload_sha256=payload_sha256,
            requested_at=utc_now_iso(),
            requested_by=requested_by,
            approval_scope=(
                self.APPROVAL_SCOPE
            ),
            execution_mode=(
                self.EXECUTION_MODE
            ),
            expires_at=expires.isoformat(),
            single_use=True,
            read_only=True,
            recommendation_only=True,
            automatic_remediation=False,
            allow_source_writes=False,
            allow_live_trading=False,
            allow_production_credentials=False,
            allow_network_side_effects=True,
            metadata={
                "gate_version": (
                    self.GATE_VERSION
                ),
                "approval_required": True,
                "provider_execution_enabled": (
                    False
                ),
                "gate_state": (
                    "AWAITING_APPROVAL"
                ),
            },
        )

        gate_dir = (
            self.gate_root
            / gate_id
        )

        gate_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        atomic_write_json(
            gate_dir
            / "execution_gate_request.json",
            request.to_dict(),
        )

        atomic_write_json(
            gate_dir
            / "execution_gate_state.json",
            {
                "schema_version": "1.0",
                "gate_id": gate_id,
                "provider_id": (
                    self.PROVIDER_ID
                ),
                "audit_id": (
                    manifest["audit_id"]
                ),
                "status": (
                    "AWAITING_APPROVAL"
                ),
                "created_at": (
                    request.requested_at
                ),
                "expires_at": (
                    request.expires_at
                ),
                "approved": False,
                "consumed": False,
                "revoked": False,
                "provider_executed": False,
                "automatic_remediation": (
                    False
                ),
            },
        )

        return request

    def approve(
        self,
        *,
        gate_id: str,
        approved_by: str,
    ) -> ExecutionGateApproval:
        gate_dir = (
            self.gate_root
            / gate_id
        )

        request_path = (
            gate_dir
            / "execution_gate_request.json"
        )

        state_path = (
            gate_dir
            / "execution_gate_state.json"
        )

        if not request_path.is_file():
            raise RuntimeError(
                "Execution gate request "
                "does not exist."
            )

        request = read_json(
            request_path
        )

        state = read_json(
            state_path
        )

        if state.get("revoked") is True:
            raise RuntimeError(
                "Execution gate is revoked."
            )

        if state.get("consumed") is True:
            raise RuntimeError(
                "Execution gate is already "
                "consumed."
            )

        if state.get("approved") is True:
            raise RuntimeError(
                "Execution gate is already "
                "approved."
            )

        expires_at = self._parse_datetime(
            request["expires_at"]
        )

        if expires_at <= self._now():
            raise RuntimeError(
                "Execution gate has expired."
            )

        approval = ExecutionGateApproval(
            schema_version="1.0",
            gate_id=gate_id,
            provider_id=(
                request["provider_id"]
            ),
            audit_id=request["audit_id"],
            package_readiness_sha256=(
                request[
                    "package_readiness_sha256"
                ]
            ),
            payload_sha256=(
                request["payload_sha256"]
            ),
            approval_status="APPROVED",
            approved_at=utc_now_iso(),
            approved_by=approved_by,
            expires_at=request[
                "expires_at"
            ],
            single_use=True,
            approval_scope=request[
                "approval_scope"
            ],
            execution_mode=request[
                "execution_mode"
            ],
            human_approval=True,
            automatic_remediation=False,
            allow_source_writes=False,
            allow_live_trading=False,
            allow_production_credentials=False,
            metadata={
                "approval_version": "1.0",
                "provider_execution_enabled": (
                    False
                ),
                "manual_approval_recorded": (
                    True
                ),
            },
        )

        atomic_write_json(
            gate_dir
            / "execution_gate_approval.json",
            approval.to_dict(),
        )

        state.update(
            {
                "status": "APPROVED",
                "approved": True,
                "approved_at": (
                    approval.approved_at
                ),
                "approved_by": (
                    approval.approved_by
                ),
                "provider_executed": False,
                "automatic_remediation": (
                    False
                ),
            }
        )

        atomic_write_json(
            state_path,
            state,
        )

        return approval

    def validate(
        self,
        *,
        gate_id: str,
    ) -> ExecutionGateValidation:
        (
            manifest,
            ready,
            payload,
            preparation,
        ) = self._load_context()

        gate_dir = (
            self.gate_root
            / gate_id
        )

        request_path = (
            gate_dir
            / "execution_gate_request.json"
        )

        approval_path = (
            gate_dir
            / "execution_gate_approval.json"
        )

        state_path = (
            gate_dir
            / "execution_gate_state.json"
        )

        if not request_path.is_file():
            raise RuntimeError(
                "Execution gate request "
                "does not exist."
            )

        request = read_json(
            request_path
        )

        state = read_json(
            state_path
        )

        approval = (
            read_json(approval_path)
            if approval_path.is_file()
            else {}
        )

        observed_payload_sha256 = (
            sha256_file(
                self.payload_path
            )
        )

        now = self._now()

        expires = self._parse_datetime(
            request["expires_at"]
        )

        checks = [
            self._check(
                check_id=(
                    "GATE_PROVIDER_MATCH"
                ),
                domain="PROVIDER",
                condition=(
                    request["provider_id"]
                    == self.PROVIDER_ID
                    and approval.get(
                        "provider_id"
                    )
                    == self.PROVIDER_ID
                ),
                message_pass=(
                    "Provider identity matches."
                ),
                message_fail=(
                    "Provider identity mismatch."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_AUDIT_MATCH"
                ),
                domain="AUDIT",
                condition=(
                    request["audit_id"]
                    == manifest["audit_id"]
                    and approval.get(
                        "audit_id"
                    )
                    == manifest["audit_id"]
                ),
                message_pass=(
                    "Audit identity matches."
                ),
                message_fail=(
                    "Audit identity mismatch."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_PACKAGE_HASH_MATCH"
                ),
                domain="INTEGRITY",
                condition=(
                    request[
                        "package_readiness_sha256"
                    ]
                    == manifest[
                        "package_readiness_sha256"
                    ]
                    == payload[
                        "package_readiness_sha256"
                    ]
                    == preparation[
                        "package_readiness_sha256"
                    ]
                    == approval.get(
                        "package_readiness_sha256"
                    )
                ),
                message_pass=(
                    "Package hash binding "
                    "is valid."
                ),
                message_fail=(
                    "Package hash binding "
                    "is invalid."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_PAYLOAD_HASH_MATCH"
                ),
                domain="INTEGRITY",
                condition=(
                    request[
                        "payload_sha256"
                    ]
                    == preparation[
                        "payload_sha256"
                    ]
                    == observed_payload_sha256
                    == approval.get(
                        "payload_sha256"
                    )
                ),
                message_pass=(
                    "Payload hash binding "
                    "is valid."
                ),
                message_fail=(
                    "Payload hash binding "
                    "is invalid."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_HUMAN_APPROVAL"
                ),
                domain="GOVERNANCE",
                condition=(
                    state.get("approved")
                    is True
                    and approval.get(
                        "approval_status"
                    )
                    == "APPROVED"
                    and approval.get(
                        "human_approval"
                    )
                    is True
                ),
                message_pass=(
                    "Human approval is valid."
                ),
                message_fail=(
                    "Human approval is missing."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_NOT_EXPIRED"
                ),
                domain="LIFECYCLE",
                condition=(
                    expires > now
                ),
                message_pass=(
                    "Execution gate is valid."
                ),
                message_fail=(
                    "Execution gate has expired."
                ),
                evidence=[
                    (
                        "expires_at="
                        f"{request['expires_at']}"
                    )
                ],
            ),
            self._check(
                check_id=(
                    "GATE_NOT_CONSUMED"
                ),
                domain="LIFECYCLE",
                condition=(
                    state.get("consumed")
                    is False
                ),
                message_pass=(
                    "Execution gate is unused."
                ),
                message_fail=(
                    "Execution gate was already "
                    "consumed."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_NOT_REVOKED"
                ),
                domain="LIFECYCLE",
                condition=(
                    state.get("revoked")
                    is False
                ),
                message_pass=(
                    "Execution gate is active."
                ),
                message_fail=(
                    "Execution gate is revoked."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_READ_ONLY_POLICY"
                ),
                domain="SECURITY",
                condition=(
                    request["read_only"]
                    is True
                    and request[
                        "recommendation_only"
                    ]
                    is True
                    and request[
                        "automatic_remediation"
                    ]
                    is False
                    and request[
                        "allow_source_writes"
                    ]
                    is False
                    and request[
                        "allow_live_trading"
                    ]
                    is False
                    and request[
                        "allow_production_credentials"
                    ]
                    is False
                    and approval.get(
                        "automatic_remediation"
                    )
                    is False
                    and approval.get(
                        "allow_source_writes"
                    )
                    is False
                    and approval.get(
                        "allow_live_trading"
                    )
                    is False
                    and approval.get(
                        "allow_production_credentials"
                    )
                    is False
                ),
                message_pass=(
                    "Read-only execution policy "
                    "is valid."
                ),
                message_fail=(
                    "Unsafe execution policy "
                    "detected."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_PACKAGE_READY"
                ),
                domain="PACKAGE",
                condition=(
                    ready["status"]
                    == (
                        "READY_FOR_"
                        "PROVIDER_AUDIT"
                    )
                ),
                message_pass=(
                    "Package remains ready."
                ),
                message_fail=(
                    "Package is no longer ready."
                ),
            ),
            self._check(
                check_id=(
                    "GATE_PROVIDER_NOT_EXECUTED"
                ),
                domain="EXECUTION",
                condition=(
                    state.get(
                        "provider_executed"
                    )
                    is False
                ),
                message_pass=(
                    "Provider has not executed."
                ),
                message_fail=(
                    "Provider execution already "
                    "recorded."
                ),
            ),
        ]

        blocking_failures = sum(
            1
            for check in checks
            if (
                check["status"]
                == "FAIL"
                and check["blocking"]
            )
        )

        warnings = sum(
            1
            for check in checks
            if check["status"]
            == "WARN"
        )

        status = (
            "AUTHORIZED_FOR_SINGLE_EXECUTION"
            if blocking_failures == 0
            else "BLOCKED"
        )

        validation = ExecutionGateValidation(
            schema_version="1.0",
            gate_id=gate_id,
            provider_id=self.PROVIDER_ID,
            audit_id=manifest["audit_id"],
            status=status,
            validated_at=utc_now_iso(),
            checks=checks,
            blocking_failures=(
                blocking_failures
            ),
            warnings=warnings,
            valid_until=request[
                "expires_at"
            ],
            consumed=bool(
                state.get("consumed")
            ),
            revoked=bool(
                state.get("revoked")
            ),
            provider_executed=False,
            automatic_remediation=False,
            metadata={
                "gate_version": (
                    self.GATE_VERSION
                ),
                "payload_sha256": (
                    observed_payload_sha256
                ),
                "package_readiness_sha256": (
                    manifest[
                        "package_readiness_sha256"
                    ]
                ),
                "human_approval": bool(
                    state.get("approved")
                ),
                "execution_available": (
                    False
                ),
            },
        )

        atomic_write_json(
            gate_dir
            / "execution_gate_validation.json",
            validation.to_dict(),
        )

        state["status"] = status
        state["last_validated_at"] = (
            validation.validated_at
        )
        state["blocking_failures"] = (
            blocking_failures
        )

        atomic_write_json(
            state_path,
            state,
        )

        return validation

    def revoke(
        self,
        *,
        gate_id: str,
        revoked_by: str,
        reason: str,
    ) -> dict[str, Any]:
        gate_dir = (
            self.gate_root
            / gate_id
        )

        state_path = (
            gate_dir
            / "execution_gate_state.json"
        )

        if not state_path.is_file():
            raise RuntimeError(
                "Execution gate does not exist."
            )

        state = read_json(
            state_path
        )

        if state.get("consumed") is True:
            raise RuntimeError(
                "Consumed gate cannot be revoked."
            )

        if state.get("revoked") is True:
            raise RuntimeError(
                "Execution gate is already revoked."
            )

        revocation = {
            "schema_version": "1.0",
            "gate_id": gate_id,
            "provider_id": (
                self.PROVIDER_ID
            ),
            "status": "REVOKED",
            "revoked_at": utc_now_iso(),
            "revoked_by": revoked_by,
            "reason": reason,
            "provider_executed": False,
            "automatic_remediation": False,
        }

        atomic_write_json(
            gate_dir
            / "execution_gate_revocation.json",
            revocation,
        )

        state.update(
            {
                "status": "REVOKED",
                "revoked": True,
                "revoked_at": (
                    revocation["revoked_at"]
                ),
                "revoked_by": revoked_by,
                "revocation_reason": reason,
                "provider_executed": False,
                "automatic_remediation": (
                    False
                ),
            }
        )

        atomic_write_json(
            state_path,
            state,
        )

        return revocation

    def consume_without_execution(
        self,
        *,
        gate_id: str,
        reason: str,
    ) -> ExecutionGateReceipt:
        validation = self.validate(
            gate_id=gate_id
        )

        if (
            validation.status
            != "AUTHORIZED_FOR_SINGLE_EXECUTION"
        ):
            raise RuntimeError(
                "Execution gate is not valid."
            )

        gate_dir = (
            self.gate_root
            / gate_id
        )

        request = read_json(
            gate_dir
            / "execution_gate_request.json"
        )

        state_path = (
            gate_dir
            / "execution_gate_state.json"
        )

        state = read_json(
            state_path
        )

        receipt = ExecutionGateReceipt(
            schema_version="1.0",
            gate_id=gate_id,
            provider_id=self.PROVIDER_ID,
            audit_id=request["audit_id"],
            status=(
                "CONSUMED_WITHOUT_EXECUTION"
            ),
            consumed_at=utc_now_iso(),
            package_readiness_sha256=(
                request[
                    "package_readiness_sha256"
                ]
            ),
            payload_sha256=(
                request["payload_sha256"]
            ),
            execution_reference=None,
            provider_executed=False,
            automatic_remediation=False,
            metadata={
                "reason": reason,
                "single_use": True,
                "network_invocation": False,
            },
        )

        atomic_write_json(
            gate_dir
            / "execution_gate_receipt.json",
            receipt.to_dict(),
        )

        state.update(
            {
                "status": (
                    "CONSUMED_WITHOUT_EXECUTION"
                ),
                "consumed": True,
                "consumed_at": (
                    receipt.consumed_at
                ),
                "provider_executed": False,
                "automatic_remediation": (
                    False
                ),
            }
        )

        atomic_write_json(
            state_path,
            state,
        )

        return receipt
