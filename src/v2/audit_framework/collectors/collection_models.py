from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CollectionIssue:
    issue_type: str
    artifact_id: str
    message: str
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CollectionResult:
    audit_id: str
    package_dir: str
    started_at: str
    completed_at: str
    status: str
    artifacts: list[dict[str, Any]]
    issues: list[CollectionIssue]
    required_expected: int
    required_collected: int
    optional_collected: int
    total_collected: int
    aggregate_sha256: str
    source_mutation_detected: bool = False
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "audit_id": self.audit_id,
            "package_dir": self.package_dir,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "artifacts": self.artifacts,
            "issues": [
                issue.to_dict()
                for issue in self.issues
            ],
            "summary": {
                "required_expected": (
                    self.required_expected
                ),
                "required_collected": (
                    self.required_collected
                ),
                "optional_collected": (
                    self.optional_collected
                ),
                "total_collected": (
                    self.total_collected
                ),
                "aggregate_sha256": (
                    self.aggregate_sha256
                ),
                "source_mutation_detected": (
                    self.source_mutation_detected
                ),
            },
            "metadata": self.metadata,
        }
