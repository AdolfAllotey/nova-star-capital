from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderCapabilities:
    provider_id: str
    display_name: str
    adapter_version: str
    supports_read_only_audit: bool
    supports_structured_output: bool
    supports_file_evidence: bool
    supports_automatic_remediation: bool
    supports_live_execution: bool
    maximum_package_files: int | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderExecutionPolicy:
    execution_mode: str
    read_only: bool
    recommendation_only: bool
    automatic_remediation: bool
    allow_source_writes: bool
    allow_live_trading: bool
    allow_production_credentials: bool
    allow_network_side_effects: bool
    require_human_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderAuditPayload:
    schema_version: str
    provider_id: str
    adapter_version: str
    audit_id: str
    release: str
    baseline_id: str
    package_dir: str
    package_manifest_path: str
    package_readiness_sha256: str
    execution_policy: ProviderExecutionPolicy
    system_instructions: str
    audit_instructions: str
    input_files: list[dict[str, Any]]
    expected_deliverables: list[str]
    output_contract: dict[str, Any]
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "adapter_version": self.adapter_version,
            "audit_id": self.audit_id,
            "release": self.release,
            "baseline_id": self.baseline_id,
            "package_dir": self.package_dir,
            "package_manifest_path": (
                self.package_manifest_path
            ),
            "package_readiness_sha256": (
                self.package_readiness_sha256
            ),
            "execution_policy": (
                self.execution_policy.to_dict()
            ),
            "system_instructions": (
                self.system_instructions
            ),
            "audit_instructions": (
                self.audit_instructions
            ),
            "input_files": self.input_files,
            "expected_deliverables": (
                self.expected_deliverables
            ),
            "output_contract": self.output_contract,
            "metadata": self.metadata,
        }


@dataclass
class ProviderPreparationResult:
    provider_id: str
    audit_id: str
    status: str
    execution_mode: str
    prepared_at: str
    payload_path: str
    payload_sha256: str
    package_readiness_sha256: str
    checks: list[dict[str, Any]]
    blocking_failures: int
    warnings: int
    provider_executed: bool
    automatic_remediation: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
