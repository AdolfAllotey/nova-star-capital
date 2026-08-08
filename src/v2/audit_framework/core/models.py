from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .constants import (
    AUDIT_FRAMEWORK_SCHEMA_VERSION,
    AUDIT_FRAMEWORK_VERSION,
)
from .enums import (
    ArtifactRole,
    AuditProvider,
    AuditStatus,
    AuditType,
    FindingDomain,
    RecommendationCategory,
    Severity,
)


@dataclass(frozen=True)
class AuditArtifact:
    artifact_id: str
    role: ArtifactRole
    source_path: str
    package_path: str
    sha256: str
    size_bytes: int
    required: bool = True
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["role"] = self.role.value
        return payload


@dataclass(frozen=True)
class AuditTarget:
    project: str
    release: str
    baseline_id: str
    baseline_status: str
    aggregate_sha256: str | None
    source_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditRequest:
    audit_id: str
    audit_type: AuditType
    provider: AuditProvider
    status: AuditStatus
    target: AuditTarget
    created_at: str
    objectives: list[str]
    constraints: list[str]
    requested_deliverables: list[str]
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_type"] = (
            self.audit_type.value
        )
        payload["provider"] = (
            self.provider.value
        )
        payload["status"] = (
            self.status.value
        )
        payload["target"] = (
            self.target.to_dict()
        )
        payload["framework_version"] = (
            AUDIT_FRAMEWORK_VERSION
        )
        payload["schema_version"] = (
            AUDIT_FRAMEWORK_SCHEMA_VERSION
        )
        return payload


@dataclass(frozen=True)
class AuditFinding:
    finding_id: str
    title: str
    description: str
    domain: FindingDomain
    severity: Severity
    category: RecommendationCategory
    evidence: list[str]
    affected_components: list[str]
    recommendation: str
    confidence: float
    blocking: bool = False
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["domain"] = self.domain.value
        payload["severity"] = self.severity.value
        payload["category"] = self.category.value
        return payload


@dataclass
class EngineeringScore:
    architecture: float
    security: float
    performance: float
    maintainability: float
    testing: float
    documentation: float
    observability: float
    governance: float
    overall: float

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not 0.0 <= value <= 100.0:
                raise ValueError(
                    f"{name} score must be "
                    f"between 0 and 100: {value}"
                )

    def to_dict(self) -> dict[str, float]:
        self.validate()
        return asdict(self)


@dataclass
class AuditReport:
    audit_id: str
    provider: AuditProvider
    status: AuditStatus
    generated_at: str
    executive_summary: str
    findings: list[AuditFinding]
    engineering_score: EngineeringScore | None
    limitations: list[str]
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                AUDIT_FRAMEWORK_SCHEMA_VERSION
            ),
            "framework_version": (
                AUDIT_FRAMEWORK_VERSION
            ),
            "audit_id": self.audit_id,
            "provider": self.provider.value,
            "status": self.status.value,
            "generated_at": self.generated_at,
            "executive_summary": (
                self.executive_summary
            ),
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
            "engineering_score": (
                self.engineering_score.to_dict()
                if self.engineering_score
                else None
            ),
            "limitations": self.limitations,
            "metadata": self.metadata,
        }
