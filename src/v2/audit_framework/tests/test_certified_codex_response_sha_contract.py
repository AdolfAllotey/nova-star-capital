from __future__ import annotations

import hashlib
import json
import os
import unittest

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from src.v2.audit_framework.transports.codex.certified_network_transport import (
    CertifiedCodexNetworkTransport,
)
from src.v2.audit_framework.transports.contracts import (
    ProviderTransportRequest,
)


def canonical_sha256(
    payload: dict,
) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def make_request() -> ProviderTransportRequest:
    return ProviderTransportRequest(
        schema_version="1.0",
        invocation_id=(
            "INVOCATION-CODEX-SHA-CONTRACT-001"
        ),
        provider_id="OPENAI_CODEX",
        audit_id="AUDIT-SHA-CONTRACT",
        gate_id="GATE-CODEX-SHA-CONTRACT-001",
        package_readiness_sha256="a" * 64,
        payload_sha256="b" * 64,
        model="gpt-5.6",
        instructions=(
            "Return a recommendation-only "
            "audit response."
        ),
        input_text=(
            "Synthetic offline contract test."
        ),
        max_output_tokens=256,
        store=False,
        tools_enabled=False,
        network_invocation_authorized=True,
        metadata={
            "test_fixture": True,
            "read_only": True,
            "recommendation_only": True,
            "single_use": True,
            "human_approved": True,
            "certified_network_transport": True,
            "automatic_remediation": False,
            "source_writes": False,
            "live_trading": False,
        },
    )


def canonical_response_payload(
    result,
) -> dict:
    return {
        "invocation_id": result.invocation_id,
        "provider_id": result.provider_id,
        "audit_id": result.audit_id,
        "gate_id": result.gate_id,
        "status": result.status,
        "output_text": result.output_text,
        "network_invocation_performed": (
            result.network_invocation_performed
        ),
        "provider_executed": (
            result.provider_executed
        ),
    }


class FakeSuccessfulResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        return SimpleNamespace(
            id="resp_sha_contract_001",
            status="completed",
            output_text=(
                "Audit recommendation only."
            ),
        )


class CertifiedCodexResponseShaContractTests(
    unittest.TestCase
):
    def test_success_hash_matches_bridge_contract(
        self,
    ) -> None:
        fake_responses = (
            FakeSuccessfulResponses()
        )

        class FakeClient:
            responses = fake_responses

        def factory(**kwargs):
            return FakeClient()

        transport = (
            CertifiedCodexNetworkTransport(
                client_factory=factory,
                allowed_models={"gpt-5.6"},
                timeout_seconds=30,
            )
        )

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": (
                    "offline-test-key"
                )
            },
            clear=False,
        ):
            result = transport.invoke(
                make_request()
            )

        self.assertEqual(
            result.status,
            "NETWORK_SUCCESS",
        )

        self.assertEqual(
            result.response_sha256,
            canonical_sha256(
                canonical_response_payload(
                    result
                )
            ),
        )

        self.assertEqual(
            result.provider_response_id,
            "resp_sha_contract_001",
        )

        self.assertTrue(
            result.network_invocation_performed
        )

        self.assertTrue(
            result.provider_executed
        )

        self.assertEqual(
            len(fake_responses.calls),
            1,
        )

    def test_failure_hash_matches_bridge_contract(
        self,
    ) -> None:
        class FailingResponses:
            def create(
                self,
                **kwargs,
            ):
                raise TimeoutError(
                    "Synthetic offline timeout."
                )

        class FakeClient:
            responses = FailingResponses()

        def factory(**kwargs):
            return FakeClient()

        transport = (
            CertifiedCodexNetworkTransport(
                client_factory=factory,
                allowed_models={"gpt-5.6"},
                timeout_seconds=30,
            )
        )

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": (
                    "offline-test-key"
                )
            },
            clear=False,
        ):
            result = transport.invoke(
                make_request()
            )

        self.assertEqual(
            result.status,
            "NETWORK_FAILED",
        )

        self.assertEqual(
            result.response_sha256,
            canonical_sha256(
                canonical_response_payload(
                    result
                )
            ),
        )

        self.assertIsNone(
            result.provider_response_id
        )

        self.assertIsNotNone(
            result.error_type
        )

        self.assertIsNotNone(
            result.error_message
        )

        self.assertTrue(
            result.network_invocation_performed
        )

        self.assertTrue(
            result.provider_executed
        )

    def test_provider_metadata_does_not_change_hash(
        self,
    ) -> None:
        fake_responses = (
            FakeSuccessfulResponses()
        )

        class FakeClient:
            responses = fake_responses

        def factory(**kwargs):
            return FakeClient()

        transport = (
            CertifiedCodexNetworkTransport(
                client_factory=factory,
                allowed_models={"gpt-5.6"},
                timeout_seconds=30,
            )
        )

        request = make_request()

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": (
                    "offline-test-key"
                )
            },
            clear=False,
        ):
            result = transport.invoke(
                request
            )

        canonical_hash = canonical_sha256(
            canonical_response_payload(
                result
            )
        )

        altered = replace(
            result,
            provider_response_id=(
                "different-provider-id"
            ),
            retryable=True,
            error_type="SyntheticError",
            error_message=(
                "Synthetic metadata only."
            ),
        )

        self.assertEqual(
            canonical_hash,
            canonical_sha256(
                canonical_response_payload(
                    altered
                )
            ),
        )

        self.assertEqual(
            result.response_sha256,
            canonical_hash,
        )


if __name__ == "__main__":
    unittest.main()
