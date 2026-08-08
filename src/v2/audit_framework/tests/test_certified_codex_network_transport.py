from __future__ import annotations

import hashlib
import json
import os
import unittest

from types import SimpleNamespace
from unittest.mock import patch

from src.v2.audit_framework.transports.codex.certified_network_transport import (
    CertifiedCodexNetworkTransport,
)
from src.v2.audit_framework.transports.contracts import (
    ProviderTransportRequest,
)


VALID_SHA_A = "a" * 64
VALID_SHA_B = "b" * 64


def make_request(
    **overrides,
) -> ProviderTransportRequest:
    values = {
        "schema_version": "1.0",
        "invocation_id": (
            "INVOCATION-CODEX-TEST-001"
        ),
        "provider_id": "OPENAI_CODEX",
        "audit_id": (
            "RC1-ENGINEERING-AUDIT-TEST"
        ),
        "gate_id": (
            "GATE-CODEX-TEST-001"
        ),
        "package_readiness_sha256": (
            VALID_SHA_A
        ),
        "payload_sha256": VALID_SHA_B,
        "model": "gpt-5.6",
        "instructions": (
            "Perform a read-only audit. "
            "Return recommendations only."
        ),
        "input_text": (
            '{"audit": "fixture"}'
        ),
        "max_output_tokens": 4000,
        "store": False,
        "tools_enabled": False,
        "network_invocation_authorized": (
            True
        ),
        "metadata": {
            "read_only": True,
            "recommendation_only": True,
            "single_use": True,
            "human_approved": True,
            "certified_network_transport": (
                True
            ),
            "automatic_remediation": (
                False
            ),
            "source_writes": False,
            "live_trading": False,
        },
    }

    values.update(
        overrides
    )

    return ProviderTransportRequest(
        **values
    )


class FakeResponses:
    def __init__(
        self,
        *,
        response=None,
        error=None,
    ):
        self.response = response
        self.error = error
        self.calls = []

    def create(
        self,
        **kwargs,
    ):
        self.calls.append(
            kwargs
        )

        if self.error is not None:
            raise self.error

        return self.response


class FakeClient:
    def __init__(
        self,
        responses,
    ):
        self.responses = responses


class APITimeoutError(
    Exception
):
    pass


class CertifiedCodexNetworkTransportTests(
    unittest.TestCase
):
    def test_explicit_model_allowlist_is_required(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "explicit certified model allowlist",
        ):
            CertifiedCodexNetworkTransport()

    def test_empty_model_allowlist_is_rejected(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "must not be empty",
        ):
            CertifiedCodexNetworkTransport(
                allowed_models=set()
            )

    def test_successful_network_result(
        self,
    ):
        fake_response = SimpleNamespace(
            id="resp_test_001",
            status="completed",
            output_text=(
                "Audit recommendation only."
            ),
        )

        fake_responses = FakeResponses(
            response=fake_response
        )

        captured_client_options = {}

        def factory(
            **kwargs,
        ):
            captured_client_options.update(
                kwargs
            )

            return FakeClient(
                fake_responses
            )

        transport = (
            CertifiedCodexNetworkTransport(
                client_factory=factory,
                allowed_models={
                    "gpt-5.6"
                },
                timeout_seconds=30,
            )
        )

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": (
                    "test-key"
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
            result.transport_mode,
            "CERTIFIED_NETWORK",
        )

        self.assertTrue(
            result.network_invocation_performed
        )

        self.assertTrue(
            result.provider_executed
        )

        self.assertEqual(
            result.provider_response_id,
            "resp_test_001",
        )

        self.assertEqual(
            result.output_text,
            "Audit recommendation only.",
        )

        self.assertFalse(
            result.retryable
        )

        self.assertIsNone(
            result.error_type
        )

        self.assertEqual(
            captured_client_options[
                "max_retries"
            ],
            0,
        )

        self.assertEqual(
            captured_client_options[
                "timeout"
            ],
            30.0,
        )

        self.assertEqual(
            len(
                fake_responses.calls
            ),
            1,
        )

        call = (
            fake_responses.calls[0]
        )

        self.assertFalse(
            call["store"]
        )

        self.assertNotIn(
            "tools",
            call,
        )

        self.assertNotIn(
            "previous_response_id",
            call,
        )

        self.assertEqual(
            result.metadata[
                "automatic_remediation"
            ],
            False,
        )

        self.assertEqual(
            result.metadata[
                "source_writes"
            ],
            False,
        )

        self.assertEqual(
            result.metadata[
                "live_trading"
            ],
            False,
        )

    def test_request_hash_is_deterministic(
        self,
    ):
        fake_response = SimpleNamespace(
            id="resp_test_hash",
            status="completed",
            output_text="Result",
        )

        def factory(
            **kwargs,
        ):
            return FakeClient(
                FakeResponses(
                    response=fake_response
                )
            )

        transport = (
            CertifiedCodexNetworkTransport(
                client_factory=factory,
                allowed_models={
                    "gpt-5.6"
                },
            )
        )

        request = make_request()

        expected = hashlib.sha256(
            json.dumps(
                request.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": (
                    "test-key"
                )
            },
            clear=False,
        ):
            first = transport.invoke(
                request
            )

            second = transport.invoke(
                request
            )

        self.assertEqual(
            first.request_sha256,
            expected,
        )

        self.assertEqual(
            second.request_sha256,
            expected,
        )

    def test_network_authorization_required(
        self,
    ):
        transport = (
            CertifiedCodexNetworkTransport(
                allowed_models={
                    "gpt-5.6"
                }
            )
        )

        request = make_request(
            network_invocation_authorized=(
                False
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "not authorized",
        ):
            transport.invoke(
                request
            )

    def test_tools_are_rejected(
        self,
    ):
        transport = (
            CertifiedCodexNetworkTransport(
                allowed_models={
                    "gpt-5.6"
                }
            )
        )

        request = make_request(
            tools_enabled=True
        )

        with self.assertRaisesRegex(
            ValueError,
            "Tools",
        ):
            transport.invoke(
                request
            )

    def test_store_true_is_rejected(
        self,
    ):
        transport = (
            CertifiedCodexNetworkTransport(
                allowed_models={
                    "gpt-5.6"
                }
            )
        )

        request = make_request(
            store=True
        )

        with self.assertRaisesRegex(
            ValueError,
            "store=false",
        ):
            transport.invoke(
                request
            )

    def test_model_allowlist_is_enforced(
        self,
    ):
        transport = (
            CertifiedCodexNetworkTransport(
                allowed_models={
                    "gpt-5.6"
                }
            )
        )

        request = make_request(
            model="unapproved-model"
        )

        with self.assertRaisesRegex(
            ValueError,
            "allowlist",
        ):
            transport.invoke(
                request
            )

    def test_human_approval_required(
        self,
    ):
        metadata = dict(
            make_request().metadata
        )

        metadata[
            "human_approved"
        ] = False

        transport = (
            CertifiedCodexNetworkTransport(
                allowed_models={
                    "gpt-5.6"
                }
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "human approval",
        ):
            transport.invoke(
                make_request(
                    metadata=metadata
                )
            )

    def test_governance_flags_required(
        self,
    ):
        for key in (
            "automatic_remediation",
            "source_writes",
            "live_trading",
        ):
            with self.subTest(
                key=key
            ):
                metadata = dict(
                    make_request().metadata
                )

                metadata[key] = True

                transport = (
                    CertifiedCodexNetworkTransport(
                        allowed_models={
                            "gpt-5.6"
                        }
                    )
                )

                with self.assertRaises(
                    ValueError
                ):
                    transport.invoke(
                        make_request(
                            metadata=metadata
                        )
                    )

    def test_timeout_is_retryable_and_fail_closed(
        self,
    ):
        def factory(
            **kwargs,
        ):
            return FakeClient(
                FakeResponses(
                    error=(
                        APITimeoutError(
                            "timed out"
                        )
                    )
                )
            )

        transport = (
            CertifiedCodexNetworkTransport(
                client_factory=factory,
                allowed_models={
                    "gpt-5.6"
                },
            )
        )

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": (
                    "test-key"
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

        self.assertTrue(
            result.network_invocation_performed
        )

        self.assertTrue(
            result.provider_executed
        )

        self.assertTrue(
            result.retryable
        )

        self.assertEqual(
            result.error_type,
            "APITimeoutError",
        )

        self.assertEqual(
            result.metadata[
                "failed_closed"
            ],
            True,
        )

    def test_missing_sdk_fails_before_network(
        self,
    ):
        transport = (
            CertifiedCodexNetworkTransport(
                allowed_models={
                    "gpt-5.6"
                }
            )
        )

        original_import = __import__

        def import_without_openai(
            name,
            globals=None,
            locals=None,
            fromlist=(),
            level=0,
        ):
            if (
                name == "openai"
                or name.startswith(
                    "openai."
                )
            ):
                raise ModuleNotFoundError(
                    "No module named 'openai'"
                )

            return original_import(
                name,
                globals,
                locals,
                fromlist,
                level,
            )

        with (
            patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": (
                        "test-key"
                    )
                },
                clear=False,
            ),
            patch(
                "builtins.__import__",
                side_effect=import_without_openai,
            ),
        ):
            result = transport.invoke(
                make_request()
            )

        self.assertEqual(
            result.status,
            "NETWORK_FAILED",
        )

        self.assertFalse(
            result
            .network_invocation_performed
        )

        self.assertFalse(
            result.provider_executed
        )

        self.assertEqual(
            result.error_type,
            "RuntimeError",
        )

        self.assertIn(
            "SDK",
            result.error_message,
        )

    def test_missing_api_key_fails_before_network(
        self,
    ):
        transport = (
            CertifiedCodexNetworkTransport(
                allowed_models={
                    "gpt-5.6"
                }
            )
        )

        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            result = transport.invoke(
                make_request()
            )

        self.assertEqual(
            result.status,
            "NETWORK_FAILED",
        )

        self.assertFalse(
            result
            .network_invocation_performed
        )

        self.assertFalse(
            result.provider_executed
        )

        self.assertIn(
            "OPENAI_API_KEY",
            result.error_message,
        )


if __name__ == "__main__":
    unittest.main()
