from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

from src.v2.audit_framework.evidence import (
    EvidencePersistenceResult,
    ImmutableAuditEvidenceRepository,
)
from src.v2.audit_framework.transports.contracts import (
    ProviderTransportRequest,
    ProviderTransportResult,
)


class CodexEvidenceCaptureBridge:
    """
    Converts one transport request/result pair into immutable
    provider evidence.

    This bridge does not:
    - invoke the provider;
    - reserve or consume a gate;
    - modify the audit registry;
    - apply recommendations;
    - modify source code.
    """

    BRIDGE_VERSION = "1.0.0"
    PROVIDER_ID = "OPENAI_CODEX"

    def __init__(
        self,
        *,
        repository: ImmutableAuditEvidenceRepository,
    ) -> None:
        self.repository = repository

    @staticmethod
    def _canonical_sha256(
        payload: Any,
    ) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(
            encoded
        ).hexdigest()

    @staticmethod
    def _extract_output_text(
        result_payload: dict[str, Any],
    ) -> str:
        direct_output = result_payload.get(
            "output_text"
        )

        if isinstance(
            direct_output,
            str,
        ):
            return direct_output

        response = result_payload.get(
            "response"
        )

        if isinstance(
            response,
            dict,
        ):
            nested_output = response.get(
                "output_text"
            )

            if isinstance(
                nested_output,
                str,
            ):
                return nested_output

        raw_response = result_payload.get(
            "raw_response"
        )

        if isinstance(
            raw_response,
            dict,
        ):
            nested_output = raw_response.get(
                "output_text"
            )

            if isinstance(
                nested_output,
                str,
            ):
                return nested_output

        return ""

    @staticmethod
    def _extract_model(
        request_payload: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> str:
        model = result_payload.get(
            "model"
        )

        if isinstance(model, str) and model:
            return model

        model = request_payload.get(
            "model"
        )

        if isinstance(model, str) and model:
            return model

        return "UNKNOWN"

    @staticmethod
    def _extract_provider_response_id(
        result_payload: dict[str, Any],
    ) -> str | None:
        value = result_payload.get(
            "provider_response_id"
        )

        if isinstance(value, str) and value:
            return value

        response = result_payload.get(
            "response"
        )

        if isinstance(response, dict):
            value = response.get("id")

            if isinstance(value, str) and value:
                return value

        raw_response = result_payload.get(
            "raw_response"
        )

        if isinstance(
            raw_response,
            dict,
        ):
            value = raw_response.get("id")

            if isinstance(value, str) and value:
                return value

        return None

    def capture(
        self,
        *,
        request: ProviderTransportRequest,
        result: ProviderTransportResult,
        metadata: dict[str, Any] | None = None,
    ) -> EvidencePersistenceResult:
        if (
            request.provider_id
            != self.PROVIDER_ID
        ):
            raise RuntimeError(
                "Evidence request provider mismatch."
            )

        if (
            result.provider_id
            != self.PROVIDER_ID
        ):
            raise RuntimeError(
                "Evidence result provider mismatch."
            )

        if (
            result.invocation_id
            != request.invocation_id
        ):
            raise RuntimeError(
                "Evidence invocation binding mismatch."
            )

        if (
            result.gate_id
            != request.gate_id
        ):
            raise RuntimeError(
                "Evidence gate binding mismatch."
            )

        if (
            result.audit_id
            != request.audit_id
        ):
            raise RuntimeError(
                "Evidence audit binding mismatch."
            )

        request_payload = request.to_dict()
        result_payload = result.to_dict()

        request_sha256 = (
            self._canonical_sha256(
                request_payload
            )
        )

        reported_request_sha = (
            result_payload.get(
                "request_sha256"
            )
        )

        if (
            reported_request_sha
            and reported_request_sha
            != request_sha256
        ):
            raise RuntimeError(
                "Transport request SHA does not match "
                "the canonical transport request."
            )

        provider_response_payload = {
            "invocation_id": (
                result.invocation_id
            ),
            "provider_id": (
                result.provider_id
            ),
            "audit_id": (
                result.audit_id
            ),
            "gate_id": (
                result.gate_id
            ),
            "status": (
                result.status
            ),
            "output_text": (
                result.output_text
            ),
            "network_invocation_performed": (
                result
                .network_invocation_performed
            ),
            "provider_executed": (
                result.provider_executed
            ),
        }

        observed_response_sha = (
            self._canonical_sha256(
                provider_response_payload
            )
        )

        reported_response_sha = (
            result.response_sha256
        )

        if (
            reported_response_sha
            != observed_response_sha
        ):
            raise RuntimeError(
                "Transport response SHA does not match "
                "the canonical provider response payload."
            )

        response_sha256 = (
            reported_response_sha
        )

        output_text = (
            self._extract_output_text(
                result_payload
            )
        )

        return self.repository.persist(
            provider_id=self.PROVIDER_ID,
            audit_id=request.audit_id,
            gate_id=request.gate_id,
            invocation_id=(
                request.invocation_id
            ),
            package_readiness_sha256=(
                request
                .package_readiness_sha256
            ),
            payload_sha256=(
                request.payload_sha256
            ),
            request_sha256=(
                request_sha256
            ),
            response_sha256=(
                response_sha256
            ),
            provider_response_id=(
                self
                ._extract_provider_response_id(
                    result_payload
                )
            ),
            model=self._extract_model(
                request_payload,
                result_payload,
            ),
            transport_mode=(
                result.transport_mode
            ),
            provider_executed=bool(
                result.provider_executed
            ),
            network_invocation_performed=bool(
                result
                .network_invocation_performed
            ),
            raw_request=request_payload,
            raw_response=(
                provider_response_payload
            ),
            output_text=output_text,
            metadata={
                **(metadata or {}),
                "bridge_version": (
                    self.BRIDGE_VERSION
                ),
                "recommendation_only": True,
                "automatic_remediation": False,
                "source_writes": False,
                "live_trading": False,
            },
        )
