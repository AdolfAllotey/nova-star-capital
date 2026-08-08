from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
    field,
)
from typing import Any


@dataclass(frozen=True)
class ProviderTransportRequest:
    schema_version: str
    invocation_id: str
    provider_id: str
    audit_id: str
    gate_id: str
    package_readiness_sha256: str
    payload_sha256: str
    model: str
    instructions: str
    input_text: str
    max_output_tokens: int
    store: bool
    tools_enabled: bool
    network_invocation_authorized: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderTransportResult:
    schema_version: str
    invocation_id: str
    provider_id: str
    audit_id: str
    gate_id: str
    status: str
    transport_mode: str
    started_at: str
    completed_at: str
    package_readiness_sha256: str
    payload_sha256: str
    provider_response_id: str | None
    output_text: str
    request_sha256: str
    response_sha256: str
    network_invocation_performed: bool
    provider_executed: bool
    retryable: bool
    error_type: str | None
    error_message: str | None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
