from __future__ import annotations

from abc import ABC, abstractmethod

from src.v2.audit_framework.transports.contracts import (
    ProviderTransportRequest,
    ProviderTransportResult,
)


class ProviderTransport(ABC):
    """
    Provider-independent transport contract.

    A transport receives an immutable request and returns
    an immutable result. It must not update the package,
    execution gate, registry or source tree.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def transport_mode(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def invoke(
        self,
        request: ProviderTransportRequest,
    ) -> ProviderTransportResult:
        raise NotImplementedError
