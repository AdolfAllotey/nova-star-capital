from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PackageFile:
    path: str
    role: str
    sha256: str
    size_bytes: int
    required_for_audit: bool
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditPackageManifest:
    audit_id: str
    release: str
    baseline_id: str
    package_status: str
    created_at: str
    package_root: str
    provider: str
    audit_mode: str
    baseline_aggregate_sha256: str | None
    collection_aggregate_sha256: str
    package_readiness_sha256: str
    files: list[PackageFile]
    objectives: list[str]
    constraints: list[str]
    deliverables: list[str]
    recommendation_categories: list[str]
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "audit_id": self.audit_id,
            "release": self.release,
            "baseline_id": self.baseline_id,
            "package_status": self.package_status,
            "created_at": self.created_at,
            "package_root": self.package_root,
            "provider": self.provider,
            "audit_mode": self.audit_mode,
            "baseline_aggregate_sha256": (
                self.baseline_aggregate_sha256
            ),
            "collection_aggregate_sha256": (
                self.collection_aggregate_sha256
            ),
            "package_readiness_sha256": (
                self.package_readiness_sha256
            ),
            "files": [
                item.to_dict()
                for item in self.files
            ],
            "objectives": self.objectives,
            "constraints": self.constraints,
            "deliverables": self.deliverables,
            "recommendation_categories": (
                self.recommendation_categories
            ),
            "metadata": self.metadata,
        }
