from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
    field,
)
from typing import Any


@dataclass(frozen=True)
class InvocationReservation:
    schema_version: str
    reservation_id: str
    invocation_id: str
    gate_id: str
    provider_id: str
    audit_id: str
    status: str
    reserved_at: str
    package_readiness_sha256: str
    payload_sha256: str
    transport_mode: str
    network_invocation_authorized: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InvocationReceipt:
    schema_version: str
    reservation_id: str
    invocation_id: str
    gate_id: str
    provider_id: str
    audit_id: str
    status: str
    started_at: str
    completed_at: str
    package_readiness_sha256: str
    payload_sha256: str
    request_sha256: str | None
    response_sha256: str | None
    provider_response_id: str | None
    transport_mode: str
    network_invocation_performed: bool
    provider_executed: bool
    gate_consumed: bool
    retryable: bool
    error_type: str | None
    error_message: str | None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
