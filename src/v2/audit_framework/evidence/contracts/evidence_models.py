from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
    field,
)
from typing import Any


@dataclass(frozen=True)
class EvidenceArtifact:
    path: str
    role: str
    sha256: str
    size_bytes: int
    media_type: str
    immutable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceRecord:
    schema_version: str
    evidence_id: str
    provider_id: str
    audit_id: str
    gate_id: str
    invocation_id: str
    package_readiness_sha256: str
    payload_sha256: str
    request_sha256: str
    response_sha256: str
    provider_response_id: str | None
    model: str
    transport_mode: str
    provider_executed: bool
    network_invocation_performed: bool
    created_at: str
    artifacts: list[EvidenceArtifact]
    aggregate_sha256: str
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = [
            item.to_dict()
            for item in self.artifacts
        ]
        return payload


@dataclass(frozen=True)
class EvidencePersistenceResult:
    schema_version: str
    evidence_id: str
    evidence_dir: str
    status: str
    aggregate_sha256: str
    artifact_count: int
    immutable: bool
    created_at: str
    existing_record_reused: bool
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
