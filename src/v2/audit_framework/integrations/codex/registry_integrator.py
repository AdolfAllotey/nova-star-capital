from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
import fcntl
import json
import os

from src.v2.audit_framework.core.utils import (
    atomic_write_json,
    read_json,
    utc_now_iso,
)
from src.v2.audit_framework.invocations.contracts.invocation_models import (
    InvocationReceipt,
)


class CodexRegistryIntegrator:
    """
    Atomically register a completed Codex invocation,
    transport result and verified immutable evidence.

    The registry is updated only when all identity,
    governance and cryptographic bindings match.
    """

    INTEGRATOR_VERSION = "1.0.0"

    ACCEPTED_RECEIPT_STATUSES = {
        "CONSUMED_SIMULATED",
        "CONSUMED_AFTER_EXECUTION",
    }

    def __init__(
        self,
        *,
        registry_path: Path,
        history_path: Path,
    ) -> None:
        self.registry_path = (
            registry_path.resolve()
        )

        self.history_path = (
            history_path.resolve()
        )

        self.lock_path = (
            self.registry_path.parent
            / ".audit_framework_registry.lock"
        )

    @contextmanager
    def _exclusive_lock(
        self,
    ) -> Iterator[None]:
        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        descriptor = os.open(
            self.lock_path,
            os.O_CREAT | os.O_RDWR,
            0o600,
        )

        try:
            fcntl.flock(
                descriptor,
                fcntl.LOCK_EX,
            )

            yield
        finally:
            fcntl.flock(
                descriptor,
                fcntl.LOCK_UN,
            )

            os.close(descriptor)

    @staticmethod
    def _append_history(
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        encoded = (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )

        descriptor = os.open(
            path,
            os.O_CREAT
            | os.O_APPEND
            | os.O_WRONLY,
            0o600,
        )

        try:
            os.write(
                descriptor,
                encoded.encode("utf-8"),
            )

            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _validate_sha(
        value: Any,
        label: str,
    ) -> None:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character in value
            )
        ):
            raise RuntimeError(
                f"Invalid {label}."
            )

    def _validate_bindings(
        self,
        *,
        registry: dict[str, Any],
        receipt: InvocationReceipt,
        transport_result: dict[str, Any],
        evidence_binding: dict[str, Any],
        evidence_manifest: dict[str, Any],
        evidence_verification: dict[str, Any],
    ) -> None:
        if (
            receipt.status
            not in self.ACCEPTED_RECEIPT_STATUSES
        ):
            raise RuntimeError(
                "Invocation receipt is not eligible "
                "for registry integration."
            )

        if receipt.gate_consumed is not True:
            raise RuntimeError(
                "Invocation gate is not consumed."
            )

        if (
            evidence_verification.get("status")
            != "VERIFIED"
        ):
            raise RuntimeError(
                "Audit evidence is not verified."
            )

        identifiers = {
            "invocation_id": (
                receipt.invocation_id
            ),
            "gate_id": receipt.gate_id,
            "provider_id": (
                receipt.provider_id
            ),
            "audit_id": receipt.audit_id,
        }

        for key, expected in identifiers.items():
            for source_name, source in (
                (
                    "transport result",
                    transport_result,
                ),
                (
                    "evidence binding",
                    evidence_binding,
                ),
                (
                    "evidence manifest",
                    evidence_manifest,
                ),
            ):
                if source.get(key) != expected:
                    raise RuntimeError(
                        f"{source_name} {key} mismatch."
                    )

        latest_package = registry.get(
            "latest_audit_package"
        )

        latest_gate = registry.get(
            "latest_execution_gate"
        )

        if not isinstance(
            latest_package,
            dict,
        ):
            raise RuntimeError(
                "Latest audit package is missing."
            )

        if not isinstance(
            latest_gate,
            dict,
        ):
            raise RuntimeError(
                "Latest execution gate is missing."
            )

        if (
            latest_package.get("audit_id")
            != receipt.audit_id
        ):
            raise RuntimeError(
                "Registry audit binding mismatch."
            )

        if (
            latest_gate.get("gate_id")
            != receipt.gate_id
        ):
            raise RuntimeError(
                "Registry gate binding mismatch."
            )

        if (
            latest_gate.get("provider_id")
            != receipt.provider_id
        ):
            raise RuntimeError(
                "Registry provider binding mismatch."
            )

        if (
            latest_package.get(
                "package_readiness_sha256"
            )
            != receipt.package_readiness_sha256
        ):
            raise RuntimeError(
                "Registry package SHA mismatch."
            )

        if (
            latest_gate.get(
                "payload_sha256"
            )
            != receipt.payload_sha256
        ):
            raise RuntimeError(
                "Registry payload SHA mismatch."
            )

        expected_request_sha = (
            receipt.request_sha256
        )

        expected_response_sha = (
            receipt.response_sha256
        )

        self._validate_sha(
            expected_request_sha,
            "receipt request SHA",
        )

        self._validate_sha(
            expected_response_sha,
            "receipt response SHA",
        )

        for source_name, source in (
            (
                "transport result",
                transport_result,
            ),
            (
                "evidence binding",
                evidence_binding,
            ),
            (
                "evidence manifest",
                evidence_manifest,
            ),
        ):
            if (
                source.get("request_sha256")
                != expected_request_sha
            ):
                raise RuntimeError(
                    f"{source_name} request SHA mismatch."
                )

            if (
                source.get("response_sha256")
                != expected_response_sha
            ):
                raise RuntimeError(
                    f"{source_name} response SHA mismatch."
                )

        if (
            evidence_binding.get(
                "verification_status"
            )
            != "VERIFIED"
        ):
            raise RuntimeError(
                "Evidence binding is not verified."
            )

        if (
            evidence_binding.get(
                "evidence_id"
            )
            != evidence_manifest.get(
                "evidence_id"
            )
        ):
            raise RuntimeError(
                "Evidence identity mismatch."
            )

        if (
            evidence_binding.get(
                "evidence_aggregate_sha256"
            )
            != evidence_manifest.get(
                "aggregate_sha256"
            )
        ):
            raise RuntimeError(
                "Evidence aggregate SHA mismatch."
            )

        if (
            bool(
                transport_result.get(
                    "provider_executed"
                )
            )
            != receipt.provider_executed
        ):
            raise RuntimeError(
                "Provider execution state mismatch."
            )

        if (
            bool(
                transport_result.get(
                    "network_invocation_performed"
                )
            )
            != receipt.network_invocation_performed
        ):
            raise RuntimeError(
                "Network invocation state mismatch."
            )

        if (
            receipt.provider_executed
            and receipt.status
            != "CONSUMED_AFTER_EXECUTION"
        ):
            raise RuntimeError(
                "Executed provider has invalid "
                "receipt status."
            )

        if (
            not receipt.provider_executed
            and receipt.status
            != "CONSUMED_SIMULATED"
        ):
            raise RuntimeError(
                "Non-executed provider has invalid "
                "receipt status."
            )

        evidence_metadata = (
            evidence_manifest.get("metadata")
        )

        if not isinstance(
            evidence_metadata,
            dict,
        ):
            raise RuntimeError(
                "Evidence metadata is missing."
            )

        if (
            evidence_metadata.get(
                "automatic_remediation"
            )
            is not False
        ):
            raise RuntimeError(
                "Automatic remediation was enabled."
            )

        if (
            evidence_metadata.get(
                "source_writes"
            )
            is not False
        ):
            raise RuntimeError(
                "Source writes were enabled."
            )

        if (
            evidence_metadata.get(
                "live_trading"
            )
            is not False
        ):
            raise RuntimeError(
                "Live trading was enabled."
            )

        if (
            evidence_metadata.get(
                "immutable"
            )
            is not True
        ):
            raise RuntimeError(
                "Evidence is not marked immutable."
            )

    def register(
        self,
        *,
        receipt: InvocationReceipt,
        transport_result: dict[str, Any],
        evidence_binding: dict[str, Any],
        evidence_manifest: dict[str, Any],
        evidence_verification: dict[str, Any],
    ) -> dict[str, Any]:
        with self._exclusive_lock():
            registry = read_json(
                self.registry_path
            )

            self._validate_bindings(
                registry=registry,
                receipt=receipt,
                transport_result=transport_result,
                evidence_binding=evidence_binding,
                evidence_manifest=evidence_manifest,
                evidence_verification=(
                    evidence_verification
                ),
            )

            registered_at = utc_now_iso()

            invocation_record = {
                "invocation_id": (
                    receipt.invocation_id
                ),
                "reservation_id": (
                    receipt.reservation_id
                ),
                "gate_id": receipt.gate_id,
                "provider_id": (
                    receipt.provider_id
                ),
                "audit_id": receipt.audit_id,
                "status": receipt.status,
                "started_at": (
                    receipt.started_at
                ),
                "completed_at": (
                    receipt.completed_at
                ),
                "package_readiness_sha256": (
                    receipt
                    .package_readiness_sha256
                ),
                "payload_sha256": (
                    receipt.payload_sha256
                ),
                "request_sha256": (
                    receipt.request_sha256
                ),
                "response_sha256": (
                    receipt.response_sha256
                ),
                "gate_consumed": (
                    receipt.gate_consumed
                ),
                "provider_executed": (
                    receipt.provider_executed
                ),
                "network_invocation_performed": (
                    receipt
                    .network_invocation_performed
                ),
                "automatic_remediation": False,
                "registered_at": registered_at,
            }

            transport_record = {
                "invocation_id": (
                    receipt.invocation_id
                ),
                "provider_id": (
                    receipt.provider_id
                ),
                "audit_id": receipt.audit_id,
                "gate_id": receipt.gate_id,
                "transport_mode": (
                    receipt.transport_mode
                ),
                "status": (
                    transport_result.get(
                        "status"
                    )
                ),
                "request_sha256": (
                    receipt.request_sha256
                ),
                "response_sha256": (
                    receipt.response_sha256
                ),
                "provider_response_id": (
                    receipt.provider_response_id
                ),
                "provider_executed": (
                    receipt.provider_executed
                ),
                "network_invocation_performed": (
                    receipt
                    .network_invocation_performed
                ),
                "retryable": (
                    receipt.retryable
                ),
                "error_type": (
                    receipt.error_type
                ),
                "automatic_remediation": False,
                "registered_at": registered_at,
            }

            evidence_record = {
                "evidence_id": (
                    evidence_manifest[
                        "evidence_id"
                    ]
                ),
                "invocation_id": (
                    receipt.invocation_id
                ),
                "provider_id": (
                    receipt.provider_id
                ),
                "audit_id": receipt.audit_id,
                "gate_id": receipt.gate_id,
                "status": (
                    evidence_binding[
                        "evidence_status"
                    ]
                ),
                "verification_status": (
                    evidence_verification[
                        "status"
                    ]
                ),
                "evidence_dir": (
                    evidence_binding[
                        "evidence_dir"
                    ]
                ),
                "manifest_path": str(
                    Path(
                        evidence_binding[
                            "evidence_dir"
                        ]
                    )
                    / "evidence_manifest.json"
                ),
                "aggregate_sha256": (
                    evidence_manifest[
                        "aggregate_sha256"
                    ]
                ),
                "request_sha256": (
                    receipt.request_sha256
                ),
                "response_sha256": (
                    receipt.response_sha256
                ),
                "provider_executed": (
                    receipt.provider_executed
                ),
                "automatic_remediation": False,
                "immutable": True,
                "registered_at": registered_at,
            }

            registry[
                "latest_codex_invocation"
            ] = invocation_record

            registry[
                "latest_codex_transport"
            ] = transport_record

            registry[
                "latest_audit_evidence"
            ] = evidence_record

            registry[
                "updated_at"
            ] = registered_at

            registry.setdefault(
                "capabilities",
                {},
            )[
                "codex_registry_integration"
            ] = "READY"

            registry["next_phase"] = {
                "name": (
                    "CONTROLLED_CODEX_RUNNER"
                ),
                "objective": (
                    "Build the controlled runner "
                    "that performs one approved "
                    "Codex invocation and registers "
                    "verified immutable evidence."
                ),
            }

            atomic_write_json(
                self.registry_path,
                registry,
            )

            history_event = {
                "event": (
                    "CODEX_INVOCATION_REGISTERED"
                ),
                "timestamp": registered_at,
                "integrator_version": (
                    self.INTEGRATOR_VERSION
                ),
                "invocation_id": (
                    receipt.invocation_id
                ),
                "reservation_id": (
                    receipt.reservation_id
                ),
                "gate_id": receipt.gate_id,
                "provider_id": (
                    receipt.provider_id
                ),
                "audit_id": receipt.audit_id,
                "invocation_status": (
                    receipt.status
                ),
                "evidence_id": (
                    evidence_record[
                        "evidence_id"
                    ]
                ),
                "evidence_status": (
                    evidence_record["status"]
                ),
                "verification_status": (
                    evidence_record[
                        "verification_status"
                    ]
                ),
                "request_sha256": (
                    receipt.request_sha256
                ),
                "response_sha256": (
                    receipt.response_sha256
                ),
                "provider_executed": (
                    receipt.provider_executed
                ),
                "network_invocation_performed": (
                    receipt
                    .network_invocation_performed
                ),
                "automatic_remediation": False,
                "source_writes": False,
                "live_trading": False,
            }

            self._append_history(
                self.history_path,
                history_event,
            )

            return {
                "status": "REGISTERED",
                "registered_at": registered_at,
                "latest_codex_invocation": (
                    invocation_record
                ),
                "latest_codex_transport": (
                    transport_record
                ),
                "latest_audit_evidence": (
                    evidence_record
                ),
                "history_event": (
                    history_event
                ),
            }
