from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import (
    AuditArtifact,
    AuditRequest,
)


@dataclass
class AuditContext:
    request: AuditRequest
    package_dir: Path
    artifacts: list[AuditArtifact] = field(
        default_factory=list
    )
    validations: dict[str, Any] = field(
        default_factory=dict
    )
    manifest: dict[str, Any] | None = None
    provider_payload: dict[str, Any] | None = None

    def ensure_package_dir(self) -> None:
        self.package_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def to_summary(self) -> dict[str, Any]:
        return {
            "audit_id": self.request.audit_id,
            "status": self.request.status.value,
            "package_dir": str(self.package_dir),
            "artifact_count": len(
                self.artifacts
            ),
            "validation_count": len(
                self.validations
            ),
            "manifest_ready": (
                self.manifest is not None
            ),
            "provider_payload_ready": (
                self.provider_payload is not None
            ),
        }
