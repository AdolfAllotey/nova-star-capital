from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from typing import Any

from src.v2.audit_framework.core.utils import (
    utc_now_iso,
)
from src.v2.audit_framework.transports.base import (
    ProviderTransport,
)
from src.v2.audit_framework.transports.contracts import (
    ProviderTransportRequest,
    ProviderTransportResult,
)


class SimulatedCodexTransport(
    ProviderTransport
):
    PROVIDER_ID = "OPENAI_CODEX"
    TRANSPORT_MODE = "SIMULATED_NO_NETWORK"
    TRANSPORT_VERSION = "1.0.0"

    def __init__(
        self,
        *,
        fixed_output: str | None = None,
    ) -> None:
        self._fixed_output = fixed_output

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def transport_mode(self) -> str:
        return self.TRANSPORT_MODE

    @staticmethod
    def _canonical_json(
        payload: dict[str, Any],
    ) -> bytes:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def _sha256_payload(
        cls,
        payload: dict[str, Any],
    ) -> str:
        return hashlib.sha256(
            cls._canonical_json(payload)
        ).hexdigest()

    @staticmethod
    def _validate_request(
        request: ProviderTransportRequest,
    ) -> None:
        if (
            request.provider_id
            != "OPENAI_CODEX"
        ):
            raise ValueError(
                "Unsupported provider."
            )

        if not request.invocation_id:
            raise ValueError(
                "Invocation ID is required."
            )

        if not request.gate_id.startswith(
            "GATE-CODEX-"
        ):
            raise ValueError(
                "Invalid Codex gate ID."
            )

        for value, label in (
            (
                request.package_readiness_sha256,
                "package_readiness_sha256",
            ),
            (
                request.payload_sha256,
                "payload_sha256",
            ),
        ):
            if (
                len(value) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in value
                )
            ):
                raise ValueError(
                    f"Invalid {label}."
                )

        if request.store is not False:
            raise ValueError(
                "Simulated audit requests must "
                "use store=false."
            )

        if request.tools_enabled is not False:
            raise ValueError(
                "Tools must remain disabled."
            )

        if (
            request.network_invocation_authorized
            is not False
        ):
            raise ValueError(
                "Simulated transport cannot "
                "accept network authorization."
            )

        if request.max_output_tokens <= 0:
            raise ValueError(
                "max_output_tokens must be "
                "positive."
            )

    def invoke(
        self,
        request: ProviderTransportRequest,
    ) -> ProviderTransportResult:
        self._validate_request(
            request
        )

        started_at = utc_now_iso()

        request_payload = (
            request.to_dict()
        )

        request_sha256 = (
            self._sha256_payload(
                request_payload
            )
        )

        output_text = (
            self._fixed_output
            if self._fixed_output is not None
            else (
                "SIMULATED_CODEX_AUDIT_RESULT\n"
                f"audit_id={request.audit_id}\n"
                f"gate_id={request.gate_id}\n"
                f"request_sha256={request_sha256}\n"
                "network_invocation=false\n"
                "provider_executed=false\n"
                "automatic_remediation=false\n"
            )
        )

        response_payload = {
            "invocation_id": (
                request.invocation_id
            ),
            "provider_id": (
                request.provider_id
            ),
            "audit_id": request.audit_id,
            "gate_id": request.gate_id,
            "status": "SIMULATED_SUCCESS",
            "output_text": output_text,
            "network_invocation_performed": (
                False
            ),
            "provider_executed": False,
        }

        response_sha256 = (
            self._sha256_payload(
                response_payload
            )
        )

        completed_at = utc_now_iso()

        return ProviderTransportResult(
            schema_version="1.0",
            invocation_id=(
                request.invocation_id
            ),
            provider_id=request.provider_id,
            audit_id=request.audit_id,
            gate_id=request.gate_id,
            status="SIMULATED_SUCCESS",
            transport_mode=(
                self.TRANSPORT_MODE
            ),
            started_at=started_at,
            completed_at=completed_at,
            package_readiness_sha256=(
                request.package_readiness_sha256
            ),
            payload_sha256=(
                request.payload_sha256
            ),
            provider_response_id=None,
            output_text=output_text,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            network_invocation_performed=False,
            provider_executed=False,
            retryable=False,
            error_type=None,
            error_message=None,
            metadata={
                "transport_version": (
                    self.TRANSPORT_VERSION
                ),
                "tools_enabled": False,
                "store": False,
                "automatic_remediation": False,
                "source_writes": False,
                "live_trading": False,
            },
        )
