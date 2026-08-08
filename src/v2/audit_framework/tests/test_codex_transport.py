from __future__ import annotations

from dataclasses import replace
import unittest

from src.v2.audit_framework.transports import (
    ProviderTransportRequest,
    SimulatedCodexTransport,
)


class SimulatedCodexTransportTests(
    unittest.TestCase
):
    @staticmethod
    def _request(
    ) -> ProviderTransportRequest:
        return ProviderTransportRequest(
            schema_version="1.0",
            invocation_id=(
                "INVOCATION-CODEX-TEST-001"
            ),
            provider_id="OPENAI_CODEX",
            audit_id="AUDIT-TEST",
            gate_id=(
                "GATE-CODEX-TEST-001"
            ),
            package_readiness_sha256=(
                "a" * 64
            ),
            payload_sha256=(
                "b" * 64
            ),
            model="TEST_MODEL",
            instructions=(
                "Perform a simulated audit."
            ),
            input_text=(
                "Simulated package evidence."
            ),
            max_output_tokens=1000,
            store=False,
            tools_enabled=False,
            network_invocation_authorized=False,
            metadata={
                "automatic_remediation": False,
            },
        )

    def test_simulated_invocation(
        self,
    ) -> None:
        transport = (
            SimulatedCodexTransport()
        )

        result = transport.invoke(
            self._request()
        )

        self.assertEqual(
            result.status,
            "SIMULATED_SUCCESS",
        )

        self.assertEqual(
            result.transport_mode,
            "SIMULATED_NO_NETWORK",
        )

        self.assertFalse(
            result.network_invocation_performed
        )

        self.assertFalse(
            result.provider_executed
        )

        self.assertIsNone(
            result.provider_response_id
        )

    def test_deterministic_content_hashes(
        self,
    ) -> None:
        transport = (
            SimulatedCodexTransport()
        )

        first = transport.invoke(
            self._request()
        )

        second = transport.invoke(
            self._request()
        )

        self.assertEqual(
            first.request_sha256,
            second.request_sha256,
        )

        self.assertEqual(
            first.response_sha256,
            second.response_sha256,
        )

    def test_network_authorization_rejected(
        self,
    ) -> None:
        transport = (
            SimulatedCodexTransport()
        )

        request = replace(
            self._request(),
            network_invocation_authorized=True,
        )

        with self.assertRaises(
            ValueError
        ):
            transport.invoke(request)

    def test_tools_rejected(
        self,
    ) -> None:
        transport = (
            SimulatedCodexTransport()
        )

        request = replace(
            self._request(),
            tools_enabled=True,
        )

        with self.assertRaises(
            ValueError
        ):
            transport.invoke(request)

    def test_store_true_rejected(
        self,
    ) -> None:
        transport = (
            SimulatedCodexTransport()
        )

        request = replace(
            self._request(),
            store=True,
        )

        with self.assertRaises(
            ValueError
        ):
            transport.invoke(request)

    def test_invalid_hash_rejected(
        self,
    ) -> None:
        transport = (
            SimulatedCodexTransport()
        )

        request = replace(
            self._request(),
            payload_sha256="invalid",
        )

        with self.assertRaises(
            ValueError
        ):
            transport.invoke(request)


if __name__ == "__main__":
    unittest.main()
