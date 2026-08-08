from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionGateRequest:
    schema_version: str
    gate_id: str
    provider_id: str
    audit_id: str
    release: str
    package_readiness_sha256: str
    payload_sha256: str
    requested_at: str
    requested_by: str
    approval_scope: str
    execution_mode: str
    expires_at: str
    single_use: bool
    read_only: bool
    recommendation_only: bool
    automatic_remediation: bool
    allow_source_writes: bool
    allow_live_trading: bool
    allow_production_credentials: bool
    allow_network_side_effects: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionGateApproval:
    schema_version: str
    gate_id: str
    provider_id: str
    audit_id: str
    package_readiness_sha256: str
    payload_sha256: str
    approval_status: str
    approved_at: str
    approved_by: str
    expires_at: str
    single_use: bool
    approval_scope: str
    execution_mode: str
    human_approval: bool
    automatic_remediation: bool
    allow_source_writes: bool
    allow_live_trading: bool
    allow_production_credentials: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionGateValidation:
    schema_version: str
    gate_id: str
    provider_id: str
    audit_id: str
    status: str
    validated_at: str
    checks: list[dict[str, Any]]
    blocking_failures: int
    warnings: int
    valid_until: str
    consumed: bool
    revoked: bool
    provider_executed: bool
    automatic_remediation: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionGateReceipt:
    schema_version: str
    gate_id: str
    provider_id: str
    audit_id: str
    status: str
    consumed_at: str
    package_readiness_sha256: str
    payload_sha256: str
    execution_reference: str | None
    provider_executed: bool
    automatic_remediation: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
