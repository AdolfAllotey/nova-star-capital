from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import (
    AuditArtifact,
    AuditReport,
    AuditRequest,
)


class ArtifactCollector(ABC):
    @abstractmethod
    def collect(
        self,
        request: AuditRequest,
        package_dir: Path,
    ) -> list[AuditArtifact]:
        """Collect artifacts into an audit package."""


class AuditValidator(ABC):
    @abstractmethod
    def validate(
        self,
        request: AuditRequest,
        artifacts: list[AuditArtifact],
    ) -> dict[str, Any]:
        """Validate an audit target and its artifacts."""


class ManifestBuilder(ABC):
    @abstractmethod
    def build(
        self,
        request: AuditRequest,
        artifacts: list[AuditArtifact],
        validations: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a provider-independent package manifest."""


class AuditProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""

    @abstractmethod
    def execute(
        self,
        request: AuditRequest,
        package_dir: Path,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute or prepare an external audit."""


class ReportNormalizer(ABC):
    @abstractmethod
    def normalize(
        self,
        request: AuditRequest,
        provider_payload: dict[str, Any],
    ) -> AuditReport:
        """Normalize a provider report."""
