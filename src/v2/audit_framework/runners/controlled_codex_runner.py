from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import sys

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..evidence.repositories.immutable_repository import (
    ImmutableAuditEvidenceRepository,
)
from ..integrations.codex.registry_integrator import (
    CodexRegistryIntegrator,
)
from ..invocations.codex.evidence_aware_coordinator import (
    EvidenceAwareCodexInvocationCoordinator,
)
from ..transports.codex.certified_network_transport import (
    CertifiedCodexNetworkTransport,
)
from ..transports.codex.simulated_transport import (
    SimulatedCodexTransport,
)
from ..transports.contracts.transport_models import (
    ProviderTransportRequest,
)


DEFAULT_REGISTRY_PATH = Path(
    "/opt/nsc/data/preprod/audits/"
    "audit_framework/registry/"
    "audit_framework_registry.json"
)

PROVIDER_ID = "OPENAI_CODEX"
RUNNER_VERSION = "1.0.0"


class ControlledCodexRunner:
    """
    Controlled Codex execution facade.

    V1 capabilities:

    - validate the real execution inputs in read-only mode;
    - execute a complete simulation on temporary copies;
    - prove that the real registry, package and gate were not mutated;
    - reject all real provider execution attempts.

    This runner never performs automatic remediation.
    """

    def __init__(
        self,
        *,
        registry_path: Path = DEFAULT_REGISTRY_PATH,
    ) -> None:
        self.registry_path = (
            Path(registry_path).resolve()
        )

    @staticmethod
    def _read_json(
        path: Path,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise RuntimeError(
                f"Required JSON file is missing: {path}"
            )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                f"Expected JSON object: {path}"
            )

        return payload

    @staticmethod
    def _canonical_json_bytes(
        payload: Any,
    ) -> bytes:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def _canonical_sha256(
        cls,
        payload: Any,
    ) -> str:
        return hashlib.sha256(
            cls._canonical_json_bytes(
                payload
            )
        ).hexdigest()

    @staticmethod
    def _file_sha256(
        path: Path,
    ) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as handle:
            while True:
                block = handle.read(
                    1024 * 1024
                )

                if not block:
                    break

                digest.update(block)

        return digest.hexdigest()

    @staticmethod
    def _validate_sha256(
        value: Any,
        label: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character in value.lower()
            )
        ):
            raise RuntimeError(
                f"Invalid {label}."
            )

        return value.lower()

    @staticmethod
    def _validate_identifier(
        value: Any,
        label: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise RuntimeError(
                f"Invalid {label}."
            )

        return value

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(
            timezone.utc
        )

    @classmethod
    def _parse_timestamp(
        cls,
        value: Any,
        label: str,
    ) -> datetime:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise RuntimeError(
                f"Invalid {label}."
            )

        normalized = value.replace(
            "Z",
            "+00:00",
        )

        try:
            parsed = datetime.fromisoformat(
                normalized
            )
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid {label}."
            ) from exc

        if parsed.tzinfo is None:
            raise RuntimeError(
                f"{label} is not timezone-aware."
            )

        return parsed.astimezone(
            timezone.utc
        )

    @staticmethod
    def _snapshot_files(
        root: Path,
    ) -> dict[str, str]:
        if not root.exists():
            raise RuntimeError(
                f"Snapshot root is missing: {root}"
            )

        snapshot: dict[str, str] = {}

        for path in sorted(
            root.rglob("*")
        ):
            if path.is_file():
                relative = str(
                    path.relative_to(root)
                )

                snapshot[relative] = (
                    hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest()
                )

        return snapshot

    @staticmethod
    def _make_tree_writable(
        root: Path,
    ) -> None:
        for path in sorted(
            root.rglob("*")
        ):
            if path.is_dir():
                path.chmod(
                    stat.S_IRUSR
                    | stat.S_IWUSR
                    | stat.S_IXUSR
                    | stat.S_IRGRP
                    | stat.S_IXGRP
                    | stat.S_IROTH
                    | stat.S_IXOTH
                )
            elif path.is_file():
                path.chmod(
                    stat.S_IRUSR
                    | stat.S_IWUSR
                    | stat.S_IRGRP
                    | stat.S_IROTH
                )

        root.chmod(
            stat.S_IRUSR
            | stat.S_IWUSR
            | stat.S_IXUSR
            | stat.S_IRGRP
            | stat.S_IXGRP
            | stat.S_IROTH
            | stat.S_IXOTH
        )

    def _load_contract(
        self,
        *,
        require_unexpired: bool,
    ) -> dict[str, Any]:
        registry = self._read_json(
            self.registry_path
        )

        audit_package = registry.get(
            "latest_audit_package"
        )

        provider_preparation = registry.get(
            "latest_provider_preparation"
        )

        execution_gate = registry.get(
            "latest_execution_gate"
        )

        if not isinstance(
            audit_package,
            dict,
        ):
            raise RuntimeError(
                "Latest audit package is missing."
            )

        if not isinstance(
            provider_preparation,
            dict,
        ):
            raise RuntimeError(
                "Latest provider preparation is missing."
            )

        if not isinstance(
            execution_gate,
            dict,
        ):
            raise RuntimeError(
                "Latest execution gate is missing."
            )

        package_dir = Path(
            self._validate_identifier(
                audit_package.get(
                    "package_dir"
                ),
                "package directory",
            )
        ).resolve()

        manifest_path = Path(
            self._validate_identifier(
                audit_package.get(
                    "manifest_path"
                ),
                "manifest path",
            )
        ).resolve()

        payload_path = Path(
            self._validate_identifier(
                provider_preparation.get(
                    "payload_path"
                ),
                "payload path",
            )
        ).resolve()

        gate_dir = Path(
            self._validate_identifier(
                execution_gate.get(
                    "gate_dir"
                ),
                "gate directory",
            )
        ).resolve()

        if not package_dir.is_dir():
            raise RuntimeError(
                "Audit package directory is missing."
            )

        if (
            package_dir
            not in manifest_path.parents
        ):
            raise RuntimeError(
                "Manifest is outside the audit package."
            )

        if (
            package_dir
            not in payload_path.parents
        ):
            raise RuntimeError(
                "Provider payload is outside "
                "the audit package."
            )

        if (
            package_dir
            not in gate_dir.parents
        ):
            raise RuntimeError(
                "Execution gate is outside "
                "the audit package."
            )

        manifest = self._read_json(
            manifest_path
        )

        payload = self._read_json(
            payload_path
        )

        state_path = (
            gate_dir
            / "execution_gate_state.json"
        )

        request_path = (
            gate_dir
            / "execution_gate_request.json"
        )

        approval_path = (
            gate_dir
            / "execution_gate_approval.json"
        )

        validation_path = (
            gate_dir
            / "execution_gate_validation.json"
        )

        state = self._read_json(
            state_path
        )

        gate_request = self._read_json(
            request_path
        )

        gate_approval = self._read_json(
            approval_path
        )

        gate_validation = self._read_json(
            validation_path
        )

        audit_id = self._validate_identifier(
            audit_package.get(
                "audit_id"
            ),
            "audit ID",
        )

        gate_id = self._validate_identifier(
            execution_gate.get(
                "gate_id"
            ),
            "gate ID",
        )

        package_sha = self._validate_sha256(
            audit_package.get(
                "package_readiness_sha256"
            ),
            "package readiness SHA256",
        )

        payload_sha = self._validate_sha256(
            provider_preparation.get(
                "payload_sha256"
            ),
            "payload SHA256",
        )

        observed_payload_sha = (
            self._file_sha256(
                payload_path
            )
        )

        if (
            observed_payload_sha
            != payload_sha
        ):
            raise RuntimeError(
                "Provider payload SHA mismatch."
            )

        binding_documents = [
            (
                "provider preparation",
                provider_preparation,
            ),
            (
                "execution gate registry record",
                execution_gate,
            ),
            (
                "execution gate state",
                state,
            ),
            (
                "execution gate request",
                gate_request,
            ),
            (
                "execution gate approval",
                gate_approval,
            ),
            (
                "execution gate validation",
                gate_validation,
            ),
        ]

        for (
            label,
            document,
        ) in binding_documents:
            document_audit_id = (
                document.get(
                    "audit_id"
                )
            )

            if (
                document_audit_id is not None
                and document_audit_id
                != audit_id
            ):
                raise RuntimeError(
                    f"{label} audit binding mismatch."
                )

            document_gate_id = (
                document.get(
                    "gate_id"
                )
            )

            if (
                document_gate_id is not None
                and document_gate_id
                != gate_id
            ):
                raise RuntimeError(
                    f"{label} gate binding mismatch."
                )

            document_package_sha = (
                document.get(
                    "package_readiness_sha256"
                )
            )

            if (
                document_package_sha
                is not None
                and document_package_sha
                != package_sha
            ):
                raise RuntimeError(
                    f"{label} package SHA binding mismatch."
                )

            document_payload_sha = (
                document.get(
                    "payload_sha256"
                )
            )

            if (
                document_payload_sha
                is not None
                and document_payload_sha
                != payload_sha
            ):
                raise RuntimeError(
                    f"{label} payload SHA binding mismatch."
                )

            document_provider = (
                document.get(
                    "provider_id"
                )
            )

            if (
                document_provider is not None
                and document_provider
                != PROVIDER_ID
            ):
                raise RuntimeError(
                    f"{label} provider binding mismatch."
                )

        if (
            execution_gate.get(
                "provider_id"
            )
            != PROVIDER_ID
        ):
            raise RuntimeError(
                "Registry gate provider mismatch."
            )

        if (
            state.get("provider_id")
            != PROVIDER_ID
        ):
            raise RuntimeError(
                "Gate state provider mismatch."
            )

        if (
            state.get("status")
            != "AUTHORIZED_FOR_SINGLE_EXECUTION"
        ):
            raise RuntimeError(
                "Execution gate is not authorized."
            )

        if (
            state.get("approved")
            is not True
        ):
            raise RuntimeError(
                "Execution gate is not approved."
            )

        if (
            state.get("consumed")
            is not False
        ):
            raise RuntimeError(
                "Execution gate is already consumed."
            )

        if (
            state.get("revoked")
            is not False
        ):
            raise RuntimeError(
                "Execution gate is revoked."
            )

        if (
            state.get(
                "provider_executed"
            )
            is not False
        ):
            raise RuntimeError(
                "Provider was already executed."
            )

        for (
            label,
            document,
        ) in (
            (
                "audit package",
                audit_package,
            ),
            (
                "provider preparation",
                provider_preparation,
            ),
            (
                "execution gate",
                execution_gate,
            ),
            (
                "execution gate state",
                state,
            ),
        ):
            if (
                document.get(
                    "automatic_remediation"
                )
                is not False
            ):
                raise RuntimeError(
                    f"{label} enables automatic remediation."
                )

        if (
            execution_gate.get(
                "single_use"
            )
            is not True
        ):
            raise RuntimeError(
                "Execution gate is not single-use."
            )

        if (
            execution_gate.get(
                "human_approval"
            )
            is not True
        ):
            raise RuntimeError(
                "Human approval is missing."
            )

        expires_at = self._parse_timestamp(
            state.get(
                "expires_at"
            ),
            "gate expiry",
        )

        expired = (
            expires_at
            <= self._utc_now()
        )

        if (
            require_unexpired
            and expired
        ):
            raise RuntimeError(
                "Execution gate is expired."
            )

        if (
            registry.get(
                "latest_codex_invocation"
            )
            is not None
        ):
            raise RuntimeError(
                "Registry already contains "
                "a Codex invocation."
            )

        if (
            registry.get(
                "latest_codex_transport"
            )
            is not None
        ):
            raise RuntimeError(
                "Registry already contains "
                "a Codex transport record."
            )

        if (
            registry.get(
                "latest_audit_evidence"
            )
            is not None
        ):
            raise RuntimeError(
                "Registry already contains "
                "audit evidence."
            )

        return {
            "registry": registry,
            "audit_package": audit_package,
            "provider_preparation": (
                provider_preparation
            ),
            "execution_gate": execution_gate,
            "manifest": manifest,
            "payload": payload,
            "state": state,
            "gate_request": gate_request,
            "gate_approval": gate_approval,
            "gate_validation": gate_validation,
            "registry_path": self.registry_path,
            "package_dir": package_dir,
            "manifest_path": manifest_path,
            "payload_path": payload_path,
            "gate_dir": gate_dir,
            "state_path": state_path,
            "audit_id": audit_id,
            "gate_id": gate_id,
            "package_sha256": package_sha,
            "payload_sha256": payload_sha,
            "observed_payload_sha256": (
                observed_payload_sha
            ),
            "expires_at": (
                expires_at.isoformat()
            ),
            "expired": expired,
        }

    def validate_real(
        self,
    ) -> dict[str, Any]:
        registry_before = (
            self.registry_path.read_bytes()
        )

        contract = self._load_contract(
            require_unexpired=False
        )

        package_snapshot_before = (
            self._snapshot_files(
                contract["package_dir"]
            )
        )

        registry_after = (
            self.registry_path.read_bytes()
        )

        package_snapshot_after = (
            self._snapshot_files(
                contract["package_dir"]
            )
        )

        if (
            registry_before
            != registry_after
        ):
            raise RuntimeError(
                "Real registry changed during validation."
            )

        if (
            package_snapshot_before
            != package_snapshot_after
        ):
            raise RuntimeError(
                "Real audit package changed "
                "during validation."
            )

        return {
            "schema_version": "1.0",
            "runner_version": (
                RUNNER_VERSION
            ),
            "mode": "VALIDATE_REAL_READ_ONLY",
            "status": (
                "VALID"
                if not contract["expired"]
                else "VALID_BUT_EXPIRED"
            ),
            "audit_id": (
                contract["audit_id"]
            ),
            "gate_id": (
                contract["gate_id"]
            ),
            "provider_id": PROVIDER_ID,
            "package_readiness_sha256": (
                contract[
                    "package_sha256"
                ]
            ),
            "payload_sha256": (
                contract[
                    "payload_sha256"
                ]
            ),
            "observed_payload_sha256": (
                contract[
                    "observed_payload_sha256"
                ]
            ),
            "gate_status": (
                contract["state"][
                    "status"
                ]
            ),
            "gate_consumed": (
                contract["state"][
                    "consumed"
                ]
            ),
            "provider_executed": (
                contract["state"][
                    "provider_executed"
                ]
            ),
            "expires_at": (
                contract["expires_at"]
            ),
            "expired": (
                contract["expired"]
            ),
            "automatic_remediation": (
                False
            ),
            "source_writes": False,
            "network_invocation_performed": (
                False
            ),
            "real_registry_unchanged": (
                True
            ),
            "real_package_unchanged": (
                True
            ),
        }

    def simulate(
        self,
    ) -> dict[str, Any]:
        real_registry_before = (
            self.registry_path.read_bytes()
        )

        contract = self._load_contract(
            require_unexpired=True
        )

        real_package_before = (
            self._snapshot_files(
                contract["package_dir"]
            )
        )

        real_gate_before = (
            self._snapshot_files(
                contract["gate_dir"]
            )
        )

        invocation_id = (
            "INVOCATION-CODEX-SIMULATION-"
            + self._utc_now()
            .strftime(
                "%Y%m%dT%H%M%S%fZ"
            )
        )

        with TemporaryDirectory(
            prefix=(
                "nsc-controlled-codex-"
            )
        ) as tmp:
            temporary_root = Path(tmp)

            package_copy = (
                temporary_root
                / "package"
            )

            shutil.copytree(
                contract["package_dir"],
                package_copy,
                copy_function=shutil.copy2,
            )

            self._make_tree_writable(
                package_copy
            )

            relative_gate_dir = (
                contract["gate_dir"]
                .relative_to(
                    contract["package_dir"]
                )
            )

            copied_gate_dir = (
                package_copy
                / relative_gate_dir
            )

            if not copied_gate_dir.is_dir():
                raise RuntimeError(
                    "Copied gate directory is missing."
                )

            temporary_registry_path = (
                temporary_root
                / "audit_framework_registry.json"
            )

            temporary_registry = json.loads(
                json.dumps(
                    contract["registry"]
                )
            )

            temporary_registry[
                "latest_audit_package"
            ]["package_dir"] = str(
                package_copy
            )

            relative_manifest_path = (
                contract["manifest_path"]
                .relative_to(
                    contract["package_dir"]
                )
            )

            temporary_registry[
                "latest_audit_package"
            ]["manifest_path"] = str(
                package_copy
                / relative_manifest_path
            )

            relative_payload_path = (
                contract["payload_path"]
                .relative_to(
                    contract["package_dir"]
                )
            )

            temporary_registry[
                "latest_provider_preparation"
            ]["payload_path"] = str(
                package_copy
                / relative_payload_path
            )

            temporary_registry[
                "latest_execution_gate"
            ]["gate_dir"] = str(
                copied_gate_dir
            )

            temporary_registry_path.write_text(
                json.dumps(
                    temporary_registry,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            temporary_history_path = (
                temporary_root
                / "registry_history.jsonl"
            )

            evidence_root = (
                temporary_root
                / "evidence"
            )

            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=evidence_root
                )
            )

            coordinator = (
                EvidenceAwareCodexInvocationCoordinator(
                    package_dir=package_copy,
                    gate_id=contract[
                        "gate_id"
                    ],
                    evidence_repository=(
                        repository
                    ),
                )
            )

            input_text = json.dumps(
                contract["payload"],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

            request = ProviderTransportRequest(
                schema_version="1.0",
                invocation_id=(
                    invocation_id
                ),
                provider_id=PROVIDER_ID,
                audit_id=contract[
                    "audit_id"
                ],
                gate_id=contract[
                    "gate_id"
                ],
                package_readiness_sha256=(
                    contract[
                        "package_sha256"
                    ]
                ),
                payload_sha256=(
                    contract[
                        "payload_sha256"
                    ]
                ),
                model="SIMULATED",
                instructions=(
                    "Perform a controlled, simulated, "
                    "read-only audit of the supplied "
                    "audit payload. Do not modify source "
                    "files. Do not perform remediation. "
                    "Do not use tools or network access."
                ),
                input_text=input_text,
                max_output_tokens=4000,
                store=False,
                tools_enabled=False,
                network_invocation_authorized=(
                    False
                ),
                metadata={
                    "runner": (
                        "ControlledCodexRunner"
                    ),
                    "runner_version": (
                        RUNNER_VERSION
                    ),
                    "simulation": True,
                    "temporary_fixture": True,
                    "read_only": True,
                    "recommendation_only": True,
                    "single_use": True,
                    "automatic_remediation": (
                        False
                    ),
                    "source_writes": False,
                    "live_trading": False,
                },
            )

            transport = (
                SimulatedCodexTransport()
            )

            receipt = coordinator.invoke(
                request=request,
                transport=transport,
            )

            invocation_dir = (
                coordinator.invocations_dir
                / invocation_id
            )

            transport_result_path = (
                invocation_dir
                / "transport_result.json"
            )

            binding_path = (
                invocation_dir
                / "invocation_evidence_binding.json"
            )

            receipt_path = (
                invocation_dir
                / "invocation_receipt.json"
            )

            transport_result = (
                self._read_json(
                    transport_result_path
                )
            )

            evidence_binding = (
                self._read_json(
                    binding_path
                )
            )

            persisted_receipt = (
                self._read_json(
                    receipt_path
                )
            )

            evidence_dir = Path(
                evidence_binding[
                    "evidence_dir"
                ]
            )

            evidence_manifest = (
                self._read_json(
                    evidence_dir
                    / "evidence_manifest.json"
                )
            )

            evidence_verification = (
                repository.verify(
                    evidence_dir=(
                        evidence_dir
                    )
                )
            )

            integrator = (
                CodexRegistryIntegrator(
                    registry_path=(
                        temporary_registry_path
                    ),
                    history_path=(
                        temporary_history_path
                    ),
                )
            )

            registration = (
                integrator.register(
                    receipt=receipt,
                    transport_result=(
                        transport_result
                    ),
                    evidence_binding=(
                        evidence_binding
                    ),
                    evidence_manifest=(
                        evidence_manifest
                    ),
                    evidence_verification=(
                        evidence_verification
                    ),
                )
            )

            simulated_registry = (
                self._read_json(
                    temporary_registry_path
                )
            )

            simulated_state = self._read_json(
                copied_gate_dir
                / "execution_gate_state.json"
            )

            history_lines = []

            if (
                temporary_history_path
                .is_file()
            ):
                history_lines = [
                    line
                    for line
                    in temporary_history_path
                    .read_text(
                        encoding="utf-8"
                    )
                    .splitlines()
                    if line.strip()
                ]

            if (
                receipt.status
                != "CONSUMED_SIMULATED"
            ):
                raise RuntimeError(
                    "Simulation receipt status "
                    "is invalid."
                )

            if (
                receipt.gate_consumed
                is not True
            ):
                raise RuntimeError(
                    "Copied gate was not consumed."
                )

            if (
                receipt.provider_executed
                is not False
            ):
                raise RuntimeError(
                    "Provider execution was recorded."
                )

            if (
                receipt
                .network_invocation_performed
                is not False
            ):
                raise RuntimeError(
                    "Network invocation was recorded."
                )

            if (
                simulated_state.get(
                    "consumed"
                )
                is not True
            ):
                raise RuntimeError(
                    "Copied gate state is not consumed."
                )

            if (
                evidence_verification.get(
                    "status"
                )
                != "VERIFIED"
            ):
                raise RuntimeError(
                    "Simulation evidence is not verified."
                )

            if (
                registration.get(
                    "status"
                )
                != "REGISTERED"
            ):
                raise RuntimeError(
                    "Simulation registry integration failed."
                )

            if (
                simulated_registry.get(
                    "latest_codex_invocation"
                )
                is None
            ):
                raise RuntimeError(
                    "Simulated invocation was not registered."
                )

            if (
                simulated_registry.get(
                    "latest_codex_transport"
                )
                is None
            ):
                raise RuntimeError(
                    "Simulated transport was not registered."
                )

            if (
                simulated_registry.get(
                    "latest_audit_evidence"
                )
                is None
            ):
                raise RuntimeError(
                    "Simulated evidence was not registered."
                )

            if len(history_lines) != 1:
                raise RuntimeError(
                    "Unexpected simulated history event count."
                )

            temporary_summary = {
                "receipt": persisted_receipt,
                "transport_result": (
                    transport_result
                ),
                "evidence_binding": (
                    evidence_binding
                ),
                "evidence_manifest": {
                    "evidence_id": (
                        evidence_manifest[
                            "evidence_id"
                        ]
                    ),
                    "status": (
                        evidence_binding[
                            "evidence_status"
                        ]
                    ),
                    "aggregate_sha256": (
                        evidence_manifest[
                            "aggregate_sha256"
                        ]
                    ),
                    "artifact_count": len(
                        evidence_manifest.get(
                            "artifacts",
                            [],
                        )
                    ),
                    "immutable": (
                        evidence_manifest[
                            "metadata"
                        ]["immutable"]
                    ),
                },
                "evidence_verification": {
                    "status": (
                        evidence_verification[
                            "status"
                        ]
                    ),
                    "aggregate_match": (
                        evidence_verification[
                            "aggregate_match"
                        ]
                    ),
                    "artifact_count": (
                        evidence_verification[
                            "artifact_count"
                        ]
                    ),
                },
                "registration": (
                    registration
                ),
                "history_event_count": (
                    len(history_lines)
                ),
                "copied_gate_status": (
                    simulated_state.get(
                        "status"
                    )
                ),
                "copied_gate_consumed": (
                    simulated_state.get(
                        "consumed"
                    )
                ),
            }

        real_registry_after = (
            self.registry_path.read_bytes()
        )

        real_package_after = (
            self._snapshot_files(
                contract["package_dir"]
            )
        )

        real_gate_after = (
            self._snapshot_files(
                contract["gate_dir"]
            )
        )

        if (
            real_registry_before
            != real_registry_after
        ):
            raise RuntimeError(
                "Real registry was mutated "
                "during simulation."
            )

        if (
            real_package_before
            != real_package_after
        ):
            raise RuntimeError(
                "Real audit package was mutated "
                "during simulation."
            )

        if (
            real_gate_before
            != real_gate_after
        ):
            raise RuntimeError(
                "Real execution gate was mutated "
                "during simulation."
            )

        return {
            "schema_version": "1.0",
            "runner_version": (
                RUNNER_VERSION
            ),
            "mode": (
                "CONTROLLED_SIMULATION"
            ),
            "status": (
                "SIMULATION_COMPLETED"
            ),
            "audit_id": (
                contract["audit_id"]
            ),
            "gate_id": (
                contract["gate_id"]
            ),
            "invocation_id": (
                invocation_id
            ),
            "provider_id": PROVIDER_ID,
            "transport_mode": (
                "SIMULATED_NO_NETWORK"
            ),
            "gate_consumed_in_fixture": (
                temporary_summary[
                    "copied_gate_consumed"
                ]
            ),
            "fixture_gate_status": (
                temporary_summary[
                    "copied_gate_status"
                ]
            ),
            "provider_executed": False,
            "network_invocation_performed": (
                False
            ),
            "automatic_remediation": (
                False
            ),
            "source_writes": False,
            "evidence_verification_status": (
                temporary_summary[
                    "evidence_verification"
                ]["status"]
            ),
            "evidence_aggregate_match": (
                temporary_summary[
                    "evidence_verification"
                ]["aggregate_match"]
            ),
            "evidence_artifact_count": (
                temporary_summary[
                    "evidence_verification"
                ]["artifact_count"]
            ),
            "registry_registration_status": (
                temporary_summary[
                    "registration"
                ]["status"]
            ),
            "history_event_count": (
                temporary_summary[
                    "history_event_count"
                ]
            ),
            "real_registry_unchanged": True,
            "real_package_unchanged": True,
            "real_gate_unchanged": True,
            "temporary_fixture_destroyed": (
                True
            ),
            "simulation": (
                temporary_summary
            ),
        }

    def certify_network_connection(
        self,
        *,
        model: str,
        timeout_seconds: float = 180.0,
    ) -> dict[str, Any]:
        """
        Certify the runner-to-network-transport wiring
        without invoking the provider.

        This method performs no reservation, consumes no
        execution gate, creates no invocation evidence and
        performs no network request.
        """

        if not isinstance(
            model,
            str,
        ) or not model.strip():
            raise ValueError(
                "A non-empty certified model is required."
            )

        certified_model = model.strip()

        registry_before = (
            self.registry_path.read_bytes()
        )

        contract = self._load_contract(
            require_unexpired=False
        )

        package_before = self._snapshot_files(
            contract["package_dir"]
        )

        gate_before = self._snapshot_files(
            contract["gate_dir"]
        )

        transport = CertifiedCodexNetworkTransport(
            allowed_models={
                certified_model
            },
            timeout_seconds=timeout_seconds,
        )

        if (
            transport.provider_id
            != PROVIDER_ID
        ):
            raise RuntimeError(
                "Certified transport provider mismatch."
            )

        if (
            transport.transport_mode
            != "CERTIFIED_NETWORK"
        ):
            raise RuntimeError(
                "Certified transport mode mismatch."
            )

        registry_after = (
            self.registry_path.read_bytes()
        )

        package_after = self._snapshot_files(
            contract["package_dir"]
        )

        gate_after = self._snapshot_files(
            contract["gate_dir"]
        )

        if (
            registry_before
            != registry_after
        ):
            raise RuntimeError(
                "Registry changed during offline "
                "network connection certification."
            )

        if (
            package_before
            != package_after
        ):
            raise RuntimeError(
                "Audit package changed during offline "
                "network connection certification."
            )

        if (
            gate_before
            != gate_after
        ):
            raise RuntimeError(
                "Execution gate changed during offline "
                "network connection certification."
            )

        return {
            "schema_version": "1.0",
            "runner_version": (
                RUNNER_VERSION
            ),
            "mode": (
                "CERTIFIED_NETWORK_CONNECTION_OFFLINE"
            ),
            "status": (
                "CERTIFIED_TRANSPORT_CONNECTED_NOT_INVOKED"
            ),
            "audit_id": (
                contract["audit_id"]
            ),
            "gate_id": (
                contract["gate_id"]
            ),
            "provider_id": (
                transport.provider_id
            ),
            "transport_mode": (
                transport.transport_mode
            ),
            "model": certified_model,
            "timeout_seconds": float(
                timeout_seconds
            ),
            "gate_status": (
                contract["state"]["status"]
            ),
            "gate_consumed": (
                contract["state"]["consumed"]
            ),
            "gate_revoked": (
                contract["state"]["revoked"]
            ),
            "provider_executed": False,
            "network_invocation_performed": False,
            "transport_invoked": False,
            "request_constructed": False,
            "reservation_created": False,
            "evidence_created": False,
            "registry_updated": False,
            "automatic_remediation": False,
            "source_writes": False,
            "live_trading": False,
            "real_registry_unchanged": True,
            "real_package_unchanged": True,
            "real_gate_unchanged": True,
            "execute_approved_enabled": False,
        }

    def certify_network_request(
        self,
        *,
        model: str,
        timeout_seconds: float = 180.0,
        max_output_tokens: int = 4000,
    ) -> dict[str, Any]:
        """
        Construct, validate and hash a certified network
        request without invoking the provider or reserving
        the execution gate.
        """

        if (
            not isinstance(model, str)
            or not model.strip()
        ):
            raise ValueError(
                "A non-empty certified model is required."
            )

        certified_model = model.strip()

        registry_before = (
            self.registry_path.read_bytes()
        )

        contract = self._load_contract(
            require_unexpired=True
        )

        package_before = self._snapshot_files(
            contract["package_dir"]
        )

        gate_before = self._snapshot_files(
            contract["gate_dir"]
        )

        transport = CertifiedCodexNetworkTransport(
            allowed_models={
                certified_model
            },
            timeout_seconds=timeout_seconds,
        )

        invocation_id = (
            "INVOCATION-CODEX-REQUEST-CERTIFICATION-"
            + self._utc_now().strftime(
                "%Y%m%dT%H%M%S%fZ"
            )
        )

        input_text = json.dumps(
            contract["payload"],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        request = ProviderTransportRequest(
            schema_version="1.0",
            invocation_id=invocation_id,
            provider_id=PROVIDER_ID,
            audit_id=contract["audit_id"],
            gate_id=contract["gate_id"],
            package_readiness_sha256=(
                contract["package_sha256"]
            ),
            payload_sha256=(
                contract["payload_sha256"]
            ),
            model=certified_model,
            instructions=(
                "Perform a controlled, read-only "
                "engineering audit of the supplied Nova "
                "Star Capital audit payload. Return "
                "recommendations only. Do not modify source "
                "files. Do not perform remediation. Do not "
                "use tools. Do not initiate trading or any "
                "external side effect."
            ),
            input_text=input_text,
            max_output_tokens=(
                int(max_output_tokens)
            ),
            store=False,
            tools_enabled=False,
            network_invocation_authorized=True,
            metadata={
                "runner": (
                    "ControlledCodexRunner"
                ),
                "runner_version": (
                    RUNNER_VERSION
                ),
                "request_certification": True,
                "read_only": True,
                "recommendation_only": True,
                "single_use": True,
                "human_approved": True,
                "certified_network_transport": True,
                "automatic_remediation": False,
                "source_writes": False,
                "live_trading": False,
            },
        )

        transport._validate_request(
            request
        )

        request_payload = (
            request.to_dict()
        )

        request_sha256 = (
            transport._sha256_payload(
                request_payload
            )
        )

        repeated_request_sha256 = (
            transport._sha256_payload(
                request.to_dict()
            )
        )

        if (
            request_sha256
            != repeated_request_sha256
        ):
            raise RuntimeError(
                "Certified request hash is not deterministic."
            )

        registry_after = (
            self.registry_path.read_bytes()
        )

        package_after = self._snapshot_files(
            contract["package_dir"]
        )

        gate_after = self._snapshot_files(
            contract["gate_dir"]
        )

        if (
            registry_before
            != registry_after
        ):
            raise RuntimeError(
                "Registry changed during certified "
                "request preparation."
            )

        if (
            package_before
            != package_after
        ):
            raise RuntimeError(
                "Audit package changed during certified "
                "request preparation."
            )

        if (
            gate_before
            != gate_after
        ):
            raise RuntimeError(
                "Execution gate changed during certified "
                "request preparation."
            )

        return {
            "schema_version": "1.0",
            "runner_version": (
                RUNNER_VERSION
            ),
            "mode": (
                "CERTIFIED_NETWORK_REQUEST_OFFLINE"
            ),
            "status": (
                "CERTIFIED_REQUEST_READY_NOT_INVOKED"
            ),
            "audit_id": (
                contract["audit_id"]
            ),
            "gate_id": (
                contract["gate_id"]
            ),
            "invocation_id": invocation_id,
            "provider_id": (
                request.provider_id
            ),
            "transport_mode": (
                transport.transport_mode
            ),
            "model": request.model,
            "timeout_seconds": float(
                timeout_seconds
            ),
            "max_output_tokens": (
                request.max_output_tokens
            ),
            "request_sha256": (
                request_sha256
            ),
            "request_hash_deterministic": True,
            "request_validated": True,
            "request_constructed": True,
            "network_invocation_authorized": True,
            "store": request.store,
            "tools_enabled": (
                request.tools_enabled
            ),
            "read_only": True,
            "recommendation_only": True,
            "single_use": True,
            "human_approved": True,
            "certified_network_transport": True,
            "automatic_remediation": False,
            "source_writes": False,
            "live_trading": False,
            "transport_invoked": False,
            "reservation_created": False,
            "gate_consumed": False,
            "provider_executed": False,
            "network_invocation_performed": False,
            "evidence_created": False,
            "registry_updated": False,
            "real_registry_unchanged": True,
            "real_package_unchanged": True,
            "real_gate_unchanged": True,
            "execute_approved_enabled": False,
            "request_payload_returned": False,
            "input_text_returned": False,
        }

    def certify_fake_provider_pipeline(
        self,
        *,
        model: str,
        timeout_seconds: float = 180.0,
        max_output_tokens: int = 4000,
    ) -> dict[str, Any]:
        """
        Execute the complete certified transport pipeline
        with an injected fake provider on temporary copies.

        No external network connection is possible.
        The real registry, package and gate remain unchanged.
        """

        from types import SimpleNamespace
        from unittest.mock import patch

        if (
            not isinstance(model, str)
            or not model.strip()
        ):
            raise ValueError(
                "A non-empty certified model is required."
            )

        certified_model = model.strip()

        real_registry_before = (
            self.registry_path.read_bytes()
        )

        contract = self._load_contract(
            require_unexpired=True
        )

        real_package_before = self._snapshot_files(
            contract["package_dir"]
        )

        real_gate_before = self._snapshot_files(
            contract["gate_dir"]
        )

        invocation_id = (
            "INVOCATION-CODEX-FAKE-PROVIDER-"
            + self._utc_now().strftime(
                "%Y%m%dT%H%M%S%fZ"
            )
        )

        class FakeResponses:
            def __init__(self) -> None:
                self.calls: list[
                    dict[str, Any]
                ] = []

            def create(
                self,
                **kwargs: Any,
            ) -> Any:
                self.calls.append(
                    dict(kwargs)
                )

                return SimpleNamespace(
                    id=(
                        "resp_nsc_fake_provider_"
                        + invocation_id
                    ),
                    status="completed",
                    output_text=(
                        "Offline fake-provider audit "
                        "recommendation. No external "
                        "network request was performed."
                    ),
                )

        class FakeClient:
            def __init__(
                self,
                responses: FakeResponses,
            ) -> None:
                self.responses = responses

        fake_responses = FakeResponses()
        captured_client_options: dict[
            str,
            Any,
        ] = {}

        def fake_client_factory(
            **kwargs: Any,
        ) -> FakeClient:
            captured_client_options.update(
                kwargs
            )

            return FakeClient(
                fake_responses
            )

        with TemporaryDirectory(
            prefix=(
                "nsc-certified-fake-provider-"
            )
        ) as tmp:
            temporary_root = Path(tmp)

            package_copy = (
                temporary_root
                / "package"
            )

            shutil.copytree(
                contract["package_dir"],
                package_copy,
                copy_function=shutil.copy2,
            )

            self._make_tree_writable(
                package_copy
            )

            relative_gate_dir = (
                contract["gate_dir"]
                .relative_to(
                    contract["package_dir"]
                )
            )

            copied_gate_dir = (
                package_copy
                / relative_gate_dir
            )

            if not copied_gate_dir.is_dir():
                raise RuntimeError(
                    "Copied execution gate is missing."
                )

            relative_manifest_path = (
                contract["manifest_path"]
                .relative_to(
                    contract["package_dir"]
                )
            )

            relative_payload_path = (
                contract["payload_path"]
                .relative_to(
                    contract["package_dir"]
                )
            )

            temporary_registry = json.loads(
                json.dumps(
                    contract["registry"]
                )
            )

            temporary_registry[
                "latest_audit_package"
            ]["package_dir"] = str(
                package_copy
            )

            temporary_registry[
                "latest_audit_package"
            ]["manifest_path"] = str(
                package_copy
                / relative_manifest_path
            )

            temporary_registry[
                "latest_provider_preparation"
            ]["payload_path"] = str(
                package_copy
                / relative_payload_path
            )

            temporary_registry[
                "latest_execution_gate"
            ]["gate_dir"] = str(
                copied_gate_dir
            )

            temporary_registry_path = (
                temporary_root
                / "audit_framework_registry.json"
            )

            temporary_registry_path.write_text(
                json.dumps(
                    temporary_registry,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            temporary_history_path = (
                temporary_root
                / "registry_history.jsonl"
            )

            evidence_root = (
                temporary_root
                / "evidence"
            )

            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=evidence_root
                )
            )

            coordinator = (
                EvidenceAwareCodexInvocationCoordinator(
                    package_dir=package_copy,
                    gate_id=contract[
                        "gate_id"
                    ],
                    evidence_repository=(
                        repository
                    ),
                )
            )

            input_text = json.dumps(
                contract["payload"],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

            request = ProviderTransportRequest(
                schema_version="1.0",
                invocation_id=invocation_id,
                provider_id=PROVIDER_ID,
                audit_id=contract["audit_id"],
                gate_id=contract["gate_id"],
                package_readiness_sha256=(
                    contract["package_sha256"]
                ),
                payload_sha256=(
                    contract["payload_sha256"]
                ),
                model=certified_model,
                instructions=(
                    "Perform a controlled, read-only "
                    "engineering audit of the supplied "
                    "Nova Star Capital audit payload. "
                    "Return recommendations only. Do not "
                    "modify source files. Do not perform "
                    "remediation. Do not use tools. Do not "
                    "initiate trading or external side "
                    "effects."
                ),
                input_text=input_text,
                max_output_tokens=(
                    int(max_output_tokens)
                ),
                store=False,
                tools_enabled=False,
                network_invocation_authorized=True,
                metadata={
                    "runner": (
                        "ControlledCodexRunner"
                    ),
                    "runner_version": (
                        RUNNER_VERSION
                    ),
                    "fake_provider_certification": True,
                    "temporary_fixture": True,
                    "read_only": True,
                    "recommendation_only": True,
                    "single_use": True,
                    "human_approved": True,
                    "certified_network_transport": True,
                    "automatic_remediation": False,
                    "source_writes": False,
                    "live_trading": False,
                },
            )

            transport = (
                CertifiedCodexNetworkTransport(
                    client_factory=(
                        fake_client_factory
                    ),
                    allowed_models={
                        certified_model
                    },
                    timeout_seconds=(
                        timeout_seconds
                    ),
                )
            )

            with patch.dict(
                "os.environ",
                {
                    "OPENAI_API_KEY": (
                        "offline-fake-key-"
                        "never-transmitted"
                    )
                },
                clear=False,
            ):
                receipt = coordinator.invoke(
                    request=request,
                    transport=transport,
                )

            if len(fake_responses.calls) != 1:
                raise RuntimeError(
                    "Unexpected fake provider call count."
                )

            provider_call = (
                fake_responses.calls[0]
            )

            expected_provider_call_keys = {
                "model",
                "instructions",
                "input",
                "max_output_tokens",
                "store",
            }

            if (
                set(provider_call)
                != expected_provider_call_keys
            ):
                raise RuntimeError(
                    "Unexpected fake provider request shape."
                )

            if (
                provider_call.get("store")
                is not False
            ):
                raise RuntimeError(
                    "Fake provider request did not "
                    "preserve store=false."
                )

            if (
                captured_client_options.get(
                    "max_retries"
                )
                != 0
            ):
                raise RuntimeError(
                    "Certified transport retries "
                    "were not disabled."
                )

            invocation_dir = (
                coordinator.invocations_dir
                / invocation_id
            )

            transport_result_path = (
                invocation_dir
                / "transport_result.json"
            )

            evidence_binding_path = (
                invocation_dir
                / "invocation_evidence_binding.json"
            )

            receipt_path = (
                invocation_dir
                / "invocation_receipt.json"
            )

            transport_result = self._read_json(
                transport_result_path
            )

            evidence_binding = self._read_json(
                evidence_binding_path
            )

            persisted_receipt = self._read_json(
                receipt_path
            )

            evidence_dir = Path(
                evidence_binding[
                    "evidence_dir"
                ]
            )

            evidence_manifest = self._read_json(
                evidence_dir
                / "evidence_manifest.json"
            )

            evidence_verification = (
                repository.verify(
                    evidence_dir=evidence_dir
                )
            )

            integrator = (
                CodexRegistryIntegrator(
                    registry_path=(
                        temporary_registry_path
                    ),
                    history_path=(
                        temporary_history_path
                    ),
                )
            )

            registration = integrator.register(
                receipt=receipt,
                transport_result=(
                    transport_result
                ),
                evidence_binding=(
                    evidence_binding
                ),
                evidence_manifest=(
                    evidence_manifest
                ),
                evidence_verification=(
                    evidence_verification
                ),
            )

            copied_gate_state = self._read_json(
                copied_gate_dir
                / "execution_gate_state.json"
            )

            registered_registry = self._read_json(
                temporary_registry_path
            )

            history_lines = []

            if temporary_history_path.is_file():
                history_lines = [
                    line
                    for line in (
                        temporary_history_path
                        .read_text(
                            encoding="utf-8"
                        )
                        .splitlines()
                    )
                    if line.strip()
                ]

            if (
                transport_result.get("status")
                != "NETWORK_SUCCESS"
            ):
                raise RuntimeError(
                    "Fake provider transport did not "
                    "complete successfully."
                )

            if (
                transport_result.get(
                    "transport_mode"
                )
                != "CERTIFIED_NETWORK"
            ):
                raise RuntimeError(
                    "Unexpected certified transport mode."
                )

            if (
                receipt.gate_consumed
                is not True
            ):
                raise RuntimeError(
                    "Temporary gate was not consumed."
                )

            if (
                receipt.provider_executed
                is not True
            ):
                raise RuntimeError(
                    "Fake provider execution was not "
                    "recorded by the transport contract."
                )

            if (
                receipt
                .network_invocation_performed
                is not True
            ):
                raise RuntimeError(
                    "Transport invocation was not recorded."
                )

            if (
                copied_gate_state.get(
                    "consumed"
                )
                is not True
            ):
                raise RuntimeError(
                    "Copied gate state was not consumed."
                )

            if (
                evidence_verification.get(
                    "status"
                )
                != "VERIFIED"
            ):
                raise RuntimeError(
                    "Fake-provider evidence verification "
                    "failed."
                )

            if (
                registration.get("status")
                != "REGISTERED"
            ):
                raise RuntimeError(
                    "Temporary registry integration failed."
                )

            if (
                registered_registry.get(
                    "latest_codex_invocation"
                )
                is None
            ):
                raise RuntimeError(
                    "Fake-provider invocation was not "
                    "registered."
                )

            if (
                registered_registry.get(
                    "latest_codex_transport"
                )
                is None
            ):
                raise RuntimeError(
                    "Fake-provider transport was not "
                    "registered."
                )

            if (
                registered_registry.get(
                    "latest_audit_evidence"
                )
                is None
            ):
                raise RuntimeError(
                    "Fake-provider evidence was not "
                    "registered."
                )

            if len(history_lines) != 1:
                raise RuntimeError(
                    "Unexpected temporary history "
                    "event count."
                )

            temporary_summary = {
                "receipt": (
                    persisted_receipt
                ),
                "transport_result": {
                    "status": (
                        transport_result[
                            "status"
                        ]
                    ),
                    "transport_mode": (
                        transport_result[
                            "transport_mode"
                        ]
                    ),
                    "request_sha256": (
                        transport_result[
                            "request_sha256"
                        ]
                    ),
                    "response_sha256": (
                        transport_result[
                            "response_sha256"
                        ]
                    ),
                    "provider_response_id": (
                        transport_result[
                            "provider_response_id"
                        ]
                    ),
                },
                "evidence": {
                    "evidence_id": (
                        evidence_manifest[
                            "evidence_id"
                        ]
                    ),
                    "aggregate_sha256": (
                        evidence_manifest[
                            "aggregate_sha256"
                        ]
                    ),
                    "verification_status": (
                        evidence_verification[
                            "status"
                        ]
                    ),
                    "artifact_count": (
                        evidence_verification[
                            "artifact_count"
                        ]
                    ),
                },
                "registration": (
                    registration
                ),
                "history_event_count": (
                    len(history_lines)
                ),
                "copied_gate_status": (
                    copied_gate_state.get(
                        "status"
                    )
                ),
                "copied_gate_consumed": (
                    copied_gate_state.get(
                        "consumed"
                    )
                ),
                "fake_provider_call_count": (
                    len(fake_responses.calls)
                ),
                "client_timeout_seconds": (
                    captured_client_options.get(
                        "timeout"
                    )
                ),
                "client_max_retries": (
                    captured_client_options.get(
                        "max_retries"
                    )
                ),
            }

        real_registry_after = (
            self.registry_path.read_bytes()
        )

        real_package_after = self._snapshot_files(
            contract["package_dir"]
        )

        real_gate_after = self._snapshot_files(
            contract["gate_dir"]
        )

        if (
            real_registry_before
            != real_registry_after
        ):
            raise RuntimeError(
                "Real registry changed during fake "
                "provider pipeline certification."
            )

        if (
            real_package_before
            != real_package_after
        ):
            raise RuntimeError(
                "Real audit package changed during fake "
                "provider pipeline certification."
            )

        if (
            real_gate_before
            != real_gate_after
        ):
            raise RuntimeError(
                "Real execution gate changed during fake "
                "provider pipeline certification."
            )

        return {
            "schema_version": "1.0",
            "runner_version": (
                RUNNER_VERSION
            ),
            "mode": (
                "CERTIFIED_FAKE_PROVIDER_PIPELINE"
            ),
            "status": (
                "CERTIFIED_PIPELINE_EXECUTED_WITH_FAKE_PROVIDER"
            ),
            "audit_id": (
                contract["audit_id"]
            ),
            "gate_id": (
                contract["gate_id"]
            ),
            "invocation_id": invocation_id,
            "provider_id": PROVIDER_ID,
            "transport_mode": (
                "CERTIFIED_NETWORK"
            ),
            "model": certified_model,
            "fake_provider": True,
            "fake_provider_call_count": 1,
            "official_openai_client_created": False,
            "external_network_performed": False,
            "real_api_request_performed": False,
            "transport_invoke_called": True,
            "transport_contract_network_flag": True,
            "transport_contract_provider_executed": True,
            "temporary_gate_consumed": True,
            "real_gate_consumed": False,
            "evidence_created_in_fixture": True,
            "evidence_verified": True,
            "registry_updated_in_fixture": True,
            "real_registry_updated": False,
            "temporary_fixture_destroyed": True,
            "automatic_remediation": False,
            "source_writes": False,
            "live_trading": False,
            "real_registry_unchanged": True,
            "real_package_unchanged": True,
            "real_gate_unchanged": True,
            "execute_approved_enabled": False,
            "pipeline": temporary_summary,
        }

    @staticmethod
    def execute_approved() -> None:
        raise RuntimeError(
            "Real Codex execution remains disabled. "
            "The complete certified pipeline has only "
            "been approved with an injected fake provider."
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or simulate the controlled "
            "Nova Star Capital Codex audit pipeline."
        )
    )

    modes = parser.add_mutually_exclusive_group(
        required=True
    )

    modes.add_argument(
        "--simulate",
        action="store_true",
        help=(
            "Run the complete pipeline on "
            "temporary fixture copies only."
        ),
    )

    modes.add_argument(
        "--validate-real",
        action="store_true",
        help=(
            "Validate the real package and gate "
            "without reserving or consuming them."
        ),
    )

    modes.add_argument(
        "--certify-network-connection",
        action="store_true",
        help=(
            "Construct and validate the certified "
            "network transport without invoking it."
        ),
    )

    modes.add_argument(
        "--certify-network-request",
        action="store_true",
        help=(
            "Construct, validate and hash a certified "
            "network request without invoking it."
        ),
    )

    modes.add_argument(
        "--certify-fake-provider-pipeline",
        action="store_true",
        help=(
            "Execute the complete certified pipeline "
            "against an injected fake provider using "
            "temporary copies only."
        ),
    )

    modes.add_argument(
        "--execute-approved",
        action="store_true",
        help=(
            "Reserved future mode. Always blocked "
            "in runner V1."
        ),
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "Explicit certified model for offline "
            "network connection certification."
        ),
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=180.0,
        help=(
            "Certified transport timeout configuration. "
            "No provider request is performed by offline "
            "certification modes."
        ),
    )

    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=4000,
        help=(
            "Maximum output tokens encoded in the "
            "certified request."
        ),
    )

    parser.add_argument(
        "--registry-path",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help=(
            "Audit Framework registry path."
        ),
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help=(
            "Print compact JSON."
        ),
    )

    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    parser = _build_parser()

    args = parser.parse_args(
        argv
    )

    runner = ControlledCodexRunner(
        registry_path=(
            args.registry_path
        )
    )

    try:
        if args.validate_real:
            result = (
                runner.validate_real()
            )
        elif args.simulate:
            result = runner.simulate()
        elif args.certify_network_connection:
            if (
                args.model is None
                or not args.model.strip()
            ):
                raise ValueError(
                    "--model is required for offline "
                    "network connection certification."
                )

            result = (
                runner.certify_network_connection(
                    model=args.model,
                    timeout_seconds=(
                        args.timeout_seconds
                    ),
                )
            )
        elif args.certify_network_request:
            if (
                args.model is None
                or not args.model.strip()
            ):
                raise ValueError(
                    "--model is required for certified "
                    "network request preparation."
                )

            result = (
                runner.certify_network_request(
                    model=args.model,
                    timeout_seconds=(
                        args.timeout_seconds
                    ),
                    max_output_tokens=(
                        args.max_output_tokens
                    ),
                )
            )
        elif args.certify_fake_provider_pipeline:
            if (
                args.model is None
                or not args.model.strip()
            ):
                raise ValueError(
                    "--model is required for fake-provider "
                    "pipeline certification."
                )

            result = (
                runner.certify_fake_provider_pipeline(
                    model=args.model,
                    timeout_seconds=(
                        args.timeout_seconds
                    ),
                    max_output_tokens=(
                        args.max_output_tokens
                    ),
                )
            )
        elif args.execute_approved:
            runner.execute_approved()

            raise AssertionError(
                "Unreachable execution branch."
            )
        else:
            raise RuntimeError(
                "No runner mode selected."
            )

    except BaseException as exc:
        failure = {
            "schema_version": "1.0",
            "runner_version": (
                RUNNER_VERSION
            ),
            "status": "FAILED_CLOSED",
            "error_type": (
                type(exc).__name__
            ),
            "error": str(exc),
            "provider_executed": False,
            "network_invocation_performed": (
                False
            ),
            "automatic_remediation": (
                False
            ),
        }

        print(
            json.dumps(
                failure,
                ensure_ascii=False,
                indent=(
                    None
                    if args.compact
                    else 2
                ),
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=(
                None
                if args.compact
                else 2
            ),
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
