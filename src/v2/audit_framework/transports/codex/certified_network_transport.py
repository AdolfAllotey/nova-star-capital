from __future__ import annotations

import hashlib
import json
import os

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from src.v2.audit_framework.transports.base import (
    ProviderTransport,
)
from src.v2.audit_framework.transports.contracts import (
    ProviderTransportRequest,
    ProviderTransportResult,
)


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


class CertifiedCodexNetworkTransport(
    ProviderTransport
):
    """
    Controlled OpenAI Codex network transport.

    Security properties:

    - explicit network authorization required;
    - store=False required;
    - tools disabled;
    - no automatic remediation;
    - no source writes;
    - no live trading;
    - no SDK retries;
    - explicit timeout;
    - deterministic NSC request/response hashes;
    - provider output only;
    - injectable client for offline tests.
    """

    PROVIDER_ID = "OPENAI_CODEX"
    TRANSPORT_MODE = "CERTIFIED_NETWORK"
    TRANSPORT_VERSION = "1.0.0"

    DEFAULT_TIMEOUT_SECONDS = 180.0
    MIN_TIMEOUT_SECONDS = 5.0
    MAX_TIMEOUT_SECONDS = 600.0

    MIN_OUTPUT_TOKENS = 1
    MAX_OUTPUT_TOKENS = 32000

    ALLOWED_MODELS: frozenset[str] = frozenset()

    def __init__(
        self,
        *,
        timeout_seconds: float = (
            DEFAULT_TIMEOUT_SECONDS
        ),
        client_factory: (
            Callable[..., Any] | None
        ) = None,
        allowed_models: (
            set[str] | frozenset[str] | None
        ) = None,
    ) -> None:
        timeout = float(
            timeout_seconds
        )

        if (
            timeout
            < self.MIN_TIMEOUT_SECONDS
            or timeout
            > self.MAX_TIMEOUT_SECONDS
        ):
            raise ValueError(
                "timeout_seconds must be between "
                f"{self.MIN_TIMEOUT_SECONDS} and "
                f"{self.MAX_TIMEOUT_SECONDS}."
            )

        self._timeout_seconds = timeout
        self._client_factory = (
            client_factory
        )

        if allowed_models is None:
            raise ValueError(
                "An explicit certified model "
                "allowlist is required."
            )

        self._allowed_models = frozenset(
            allowed_models
        )

        if not self._allowed_models:
            raise ValueError(
                "The certified model allowlist "
                "must not be empty."
            )

        for model in self._allowed_models:
            if (
                not isinstance(model, str)
                or not model.strip()
            ):
                raise ValueError(
                    "Certified model identifiers "
                    "must be non-empty strings."
                )

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
            cls._canonical_json(
                payload
            )
        ).hexdigest()

    @staticmethod
    def _validate_sha256(
        value: str,
        label: str,
    ) -> None:
        if (
            not isinstance(
                value,
                str,
            )
            or len(value) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character in value
            )
        ):
            raise ValueError(
                f"Invalid {label}."
            )

    def _validate_request(
        self,
        request: ProviderTransportRequest,
    ) -> None:
        if (
            request.provider_id
            != self.PROVIDER_ID
        ):
            raise ValueError(
                "Invalid provider ID."
            )

        if not request.invocation_id:
            raise ValueError(
                "Invocation ID is required."
            )

        if not request.audit_id:
            raise ValueError(
                "Audit ID is required."
            )

        if (
            not request.gate_id
            or not request.gate_id.startswith(
                "GATE-CODEX-"
            )
        ):
            raise ValueError(
                "Invalid Codex gate ID."
            )

        self._validate_sha256(
            request.package_readiness_sha256,
            "package_readiness_sha256",
        )

        self._validate_sha256(
            request.payload_sha256,
            "payload_sha256",
        )

        if (
            request
            .network_invocation_authorized
            is not True
        ):
            raise ValueError(
                "Network invocation is not authorized."
            )

        if request.store is not False:
            raise ValueError(
                "Certified audit requests must "
                "use store=false."
            )

        if request.tools_enabled is not False:
            raise ValueError(
                "Tools must remain disabled."
            )

        if (
            request.model
            not in self._allowed_models
        ):
            raise ValueError(
                "Model is not in the certified "
                "allowlist."
            )

        if (
            not isinstance(
                request.instructions,
                str,
            )
            or not request.instructions.strip()
        ):
            raise ValueError(
                "Instructions are required."
            )

        if (
            not isinstance(
                request.input_text,
                str,
            )
            or not request.input_text.strip()
        ):
            raise ValueError(
                "Input text is required."
            )

        if (
            request.max_output_tokens
            < self.MIN_OUTPUT_TOKENS
            or request.max_output_tokens
            > self.MAX_OUTPUT_TOKENS
        ):
            raise ValueError(
                "max_output_tokens is outside "
                "the certified range."
            )

        metadata = request.metadata

        if not isinstance(
            metadata,
            dict,
        ):
            raise ValueError(
                "Request metadata must be a dictionary."
            )

        required_false = (
            "automatic_remediation",
            "source_writes",
            "live_trading",
        )

        for key in required_false:
            if metadata.get(key) is not False:
                raise ValueError(
                    f"{key} must be false."
                )

        required_true = (
            "read_only",
            "recommendation_only",
            "single_use",
        )

        for key in required_true:
            if metadata.get(key) is not True:
                raise ValueError(
                    f"{key} must be true."
                )

        if metadata.get(
            "human_approved"
        ) is not True:
            raise ValueError(
                "Explicit human approval is required."
            )

        if metadata.get(
            "certified_network_transport"
        ) is not True:
            raise ValueError(
                "Certified network transport "
                "binding is required."
            )

    def _build_client(
        self,
    ) -> Any:
        api_key = os.environ.get(
            "OPENAI_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        if (
            self._client_factory
            is not None
        ):
            return self._client_factory(
                api_key=api_key,
                timeout=self._timeout_seconds,
                max_retries=0,
            )

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The official OpenAI SDK is not "
                "installed. Network execution remains "
                "disabled."
            ) from exc

        return OpenAI(
            api_key=api_key,
            timeout=self._timeout_seconds,
            max_retries=0,
        )

    @staticmethod
    def _extract_output_text(
        response: Any,
    ) -> str:
        output_text = getattr(
            response,
            "output_text",
            None,
        )

        if (
            isinstance(
                output_text,
                str,
            )
            and output_text.strip()
        ):
            return output_text

        output = getattr(
            response,
            "output",
            None,
        )

        if not isinstance(
            output,
            list,
        ):
            raise RuntimeError(
                "Provider response contains no "
                "usable output."
            )

        fragments: list[str] = []

        for item in output:
            content = getattr(
                item,
                "content",
                None,
            )

            if not isinstance(
                content,
                list,
            ):
                continue

            for part in content:
                text = getattr(
                    part,
                    "text",
                    None,
                )

                if (
                    isinstance(
                        text,
                        str,
                    )
                    and text
                ):
                    fragments.append(
                        text
                    )

        joined = "\n".join(
            fragments
        ).strip()

        if not joined:
            raise RuntimeError(
                "Provider response contains no "
                "text output."
            )

        return joined

    @staticmethod
    def _provider_response_id(
        response: Any,
    ) -> str:
        response_id = getattr(
            response,
            "id",
            None,
        )

        if (
            not isinstance(
                response_id,
                str,
            )
            or not response_id.strip()
        ):
            raise RuntimeError(
                "Provider response ID is missing."
            )

        return response_id

    @staticmethod
    def _provider_status(
        response: Any,
    ) -> str | None:
        status = getattr(
            response,
            "status",
            None,
        )

        if status is None:
            return None

        return str(status)

    @staticmethod
    def _classify_error(
        exc: Exception,
    ) -> tuple[bool, str]:
        name = type(exc).__name__

        retryable_types = {
            "APIConnectionError",
            "APITimeoutError",
            "RateLimitError",
            "InternalServerError",
        }

        retryable = (
            name in retryable_types
        )

        return (
            retryable,
            name,
        )

    def invoke(
        self,
        request: ProviderTransportRequest,
    ) -> ProviderTransportResult:
        self._validate_request(
            request
        )

        request_payload = (
            request.to_dict()
        )

        request_sha256 = (
            self._sha256_payload(
                request_payload
            )
        )

        started_at = utc_now_iso()

        network_started = False

        try:
            client = self._build_client()

            network_started = True

            response = (
                client.responses.create(
                    model=request.model,
                    instructions=(
                        request.instructions
                    ),
                    input=request.input_text,
                    max_output_tokens=(
                        request
                        .max_output_tokens
                    ),
                    store=False,
                )
            )

            provider_response_id = (
                self._provider_response_id(
                    response
                )
            )

            provider_status = (
                self._provider_status(
                    response
                )
            )

            if (
                provider_status
                not in (
                    None,
                    "completed",
                )
            ):
                raise RuntimeError(
                    "Provider response did not "
                    "complete successfully: "
                    f"{provider_status}"
                )

            output_text = (
                self._extract_output_text(
                    response
                )
            )

            response_payload = {
                "invocation_id": (
                    request.invocation_id
                ),
                "provider_id": (
                    request.provider_id
                ),
                "audit_id": (
                    request.audit_id
                ),
                "gate_id": (
                    request.gate_id
                ),
                "status": (
                    "NETWORK_SUCCESS"
                ),
                "output_text": (
                    output_text
                ),
                "network_invocation_performed": (
                    True
                ),
                "provider_executed": True,
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
                provider_id=(
                    request.provider_id
                ),
                audit_id=request.audit_id,
                gate_id=request.gate_id,
                status="NETWORK_SUCCESS",
                transport_mode=(
                    self.TRANSPORT_MODE
                ),
                started_at=started_at,
                completed_at=completed_at,
                package_readiness_sha256=(
                    request
                    .package_readiness_sha256
                ),
                payload_sha256=(
                    request.payload_sha256
                ),
                provider_response_id=(
                    provider_response_id
                ),
                output_text=output_text,
                request_sha256=(
                    request_sha256
                ),
                response_sha256=(
                    response_sha256
                ),
                network_invocation_performed=(
                    True
                ),
                provider_executed=True,
                retryable=False,
                error_type=None,
                error_message=None,
                metadata={
                    "transport_version": (
                        self.TRANSPORT_VERSION
                    ),
                    "provider_response_status": (
                        provider_status
                    ),
                    "tools_enabled": False,
                    "store": False,
                    "sdk_max_retries": 0,
                    "timeout_seconds": (
                        self._timeout_seconds
                    ),
                    "automatic_remediation": (
                        False
                    ),
                    "source_writes": False,
                    "live_trading": False,
                    "read_only": True,
                    "recommendation_only": True,
                },
            )

        except Exception as exc:
            retryable, error_type = (
                self._classify_error(
                    exc
                )
            )

            completed_at = utc_now_iso()

            error_message = str(exc)

            response_payload = {
                "invocation_id": (
                    request.invocation_id
                ),
                "provider_id": (
                    request.provider_id
                ),
                "audit_id": (
                    request.audit_id
                ),
                "gate_id": (
                    request.gate_id
                ),
                "status": (
                    "NETWORK_FAILED"
                ),
                "output_text": "",
                "network_invocation_performed": (
                    network_started
                ),
                "provider_executed": (
                    network_started
                ),
            }

            response_sha256 = (
                self._sha256_payload(
                    response_payload
                )
            )

            return ProviderTransportResult(
                schema_version="1.0",
                invocation_id=(
                    request.invocation_id
                ),
                provider_id=(
                    request.provider_id
                ),
                audit_id=request.audit_id,
                gate_id=request.gate_id,
                status="NETWORK_FAILED",
                transport_mode=(
                    self.TRANSPORT_MODE
                ),
                started_at=started_at,
                completed_at=completed_at,
                package_readiness_sha256=(
                    request
                    .package_readiness_sha256
                ),
                payload_sha256=(
                    request.payload_sha256
                ),
                provider_response_id=None,
                output_text="",
                request_sha256=(
                    request_sha256
                ),
                response_sha256=(
                    response_sha256
                ),
                network_invocation_performed=(
                    network_started
                ),
                provider_executed=(
                    network_started
                ),
                retryable=retryable,
                error_type=error_type,
                error_message=(
                    error_message
                ),
                metadata={
                    "transport_version": (
                        self.TRANSPORT_VERSION
                    ),
                    "tools_enabled": False,
                    "store": False,
                    "sdk_max_retries": 0,
                    "timeout_seconds": (
                        self._timeout_seconds
                    ),
                    "automatic_remediation": (
                        False
                    ),
                    "source_writes": False,
                    "live_trading": False,
                    "read_only": True,
                    "recommendation_only": True,
                    "failed_closed": True,
                },
            )
