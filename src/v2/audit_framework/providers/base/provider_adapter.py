from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.v2.audit_framework.providers.contracts import (
    ProviderAuditPayload,
    ProviderCapabilities,
    ProviderPreparationResult,
)


class ProviderAdapter(ABC):
    """
    Provider-independent audit adapter contract.

    Preparation and execution are intentionally separate.
    """

    @property
    @abstractmethod
    def capabilities(
        self,
    ) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def validate_package(
        self,
        package_dir: Path,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def build_payload(
        self,
        package_dir: Path,
    ) -> ProviderAuditPayload:
        raise NotImplementedError

    @abstractmethod
    def prepare(
        self,
        package_dir: Path,
    ) -> ProviderPreparationResult:
        raise NotImplementedError

    def execute(
        self,
        payload: ProviderAuditPayload,
    ) -> None:
        raise RuntimeError(
            "Provider execution is disabled in "
            "Provider Adapter v1. Preparation only."
        )
