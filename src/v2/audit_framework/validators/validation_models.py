from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    domain: str
    status: str
    message: str
    blocking: bool
    expected: Any = None
    observed: Any = None
    evidence: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BaselineValidationResult:
    audit_id: str
    baseline_id: str
    release: str
    started_at: str
    completed_at: str
    status: str
    checks: list[ValidationCheck]
    blocking_failures: int
    warnings: int
    passed: int
    aggregate_sha256: str | None
    package_integrity_sha256: str | None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "audit_id": self.audit_id,
            "baseline_id": self.baseline_id,
            "release": self.release,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
            "summary": {
                "passed": self.passed,
                "warnings": self.warnings,
                "blocking_failures": (
                    self.blocking_failures
                ),
                "total_checks": len(
                    self.checks
                ),
                "aggregate_sha256": (
                    self.aggregate_sha256
                ),
                "package_integrity_sha256": (
                    self.package_integrity_sha256
                ),
            },
            "metadata": self.metadata,
        }
