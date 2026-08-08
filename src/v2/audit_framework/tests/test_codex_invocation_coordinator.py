from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.v2.audit_framework.invocations import (
    CodexInvocationCoordinator,
)
from src.v2.audit_framework.transports import (
    ProviderTransportRequest,
    SimulatedCodexTransport,
)


class CodexInvocationCoordinatorTests(
    unittest.TestCase
):
    PACKAGE_SHA = "a" * 64
    PAYLOAD_SHA = "b" * 64
    GATE_ID = "GATE-CODEX-TEST-001"

    @classmethod
    def _create_fixture(
        cls,
        root: Path,
    ) -> Path:
        package_dir = root / "package"

        gate_dir = (
            package_dir
            / "execution_gates"
            / "openai_codex"
            / cls.GATE_ID
        )

        gate_dir.mkdir(
            parents=True
        )

        request = {
            "schema_version": "1.0",
            "gate_id": cls.GATE_ID,
            "provider_id": "OPENAI_CODEX",
            "audit_id": "AUDIT-TEST",
            "release": "RC1",
            "package_readiness_sha256": (
                cls.PACKAGE_SHA
            ),
            "payload_sha256": (
                cls.PAYLOAD_SHA
            ),
            "requested_at": (
                "2026-07-25T00:00:00+00:00"
            ),
            "requested_by": "TEST",
            "approval_scope": (
                "RC1_ENGINEERING_AUDIT_READ_ONLY"
            ),
            "execution_mode": (
                "CONTROLLED_PROVIDER_AUDIT"
            ),
            "expires_at": (
                "2099-01-01T00:00:00+00:00"
            ),
            "single_use": True,
            "read_only": True,
            "recommendation_only": True,
            "automatic_remediation": False,
            "allow_source_writes": False,
            "allow_live_trading": False,
            "allow_production_credentials": False,
            "allow_network_side_effects": True,
            "metadata": {},
        }

        state = {
            "schema_version": "1.0",
            "gate_id": cls.GATE_ID,
            "provider_id": "OPENAI_CODEX",
            "audit_id": "AUDIT-TEST",
            "status": (
                "AUTHORIZED_FOR_SINGLE_EXECUTION"
            ),
            "approved": True,
            "consumed": False,
            "revoked": False,
            "provider_executed": False,
            "automatic_remediation": False,
        }

        (
            gate_dir
            / "execution_gate_request.json"
        ).write_text(
            json.dumps(
                request,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            gate_dir
            / "execution_gate_state.json"
        ).write_text(
            json.dumps(
                state,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return package_dir

    @classmethod
    def _request(
        cls,
        *,
        invocation_id: str = (
            "INVOCATION-CODEX-TEST-001"
        ),
    ) -> ProviderTransportRequest:
        return ProviderTransportRequest(
            schema_version="1.0",
            invocation_id=invocation_id,
            provider_id="OPENAI_CODEX",
            audit_id="AUDIT-TEST",
            gate_id=cls.GATE_ID,
            package_readiness_sha256=(
                cls.PACKAGE_SHA
            ),
            payload_sha256=(
                cls.PAYLOAD_SHA
            ),
            model="SIMULATED",
            instructions=(
                "Perform simulated audit."
            ),
            input_text="Test evidence.",
            max_output_tokens=1000,
            store=False,
            tools_enabled=False,
            network_invocation_authorized=False,
            metadata={
                "automatic_remediation": False,
            },
        )

    def test_simulated_gate_consumption(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            package_dir = (
                self._create_fixture(
                    Path(tmp)
                )
            )

            coordinator = (
                CodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                )
            )

            receipt = coordinator.invoke(
                request=self._request(),
                transport=(
                    SimulatedCodexTransport()
                ),
            )

            self.assertEqual(
                receipt.status,
                "CONSUMED_SIMULATED",
            )

            self.assertTrue(
                receipt.gate_consumed
            )

            self.assertFalse(
                receipt.provider_executed
            )

            self.assertFalse(
                receipt
                .network_invocation_performed
            )

            state = json.loads(
                coordinator.state_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertTrue(
                state["consumed"]
            )

            self.assertEqual(
                state["status"],
                "CONSUMED_SIMULATED",
            )

    def test_second_invocation_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            package_dir = (
                self._create_fixture(
                    Path(tmp)
                )
            )

            coordinator = (
                CodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                )
            )

            coordinator.invoke(
                request=self._request(),
                transport=(
                    SimulatedCodexTransport()
                ),
            )

            with self.assertRaises(
                RuntimeError
            ):
                coordinator.invoke(
                    request=self._request(
                        invocation_id=(
                            "INVOCATION-CODEX-TEST-002"
                        )
                    ),
                    transport=(
                        SimulatedCodexTransport()
                    ),
                )

    def test_payload_binding_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            package_dir = (
                self._create_fixture(
                    Path(tmp)
                )
            )

            coordinator = (
                CodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                )
            )

            request = self._request()

            invalid_request = (
                ProviderTransportRequest(
                    **{
                        **request.to_dict(),
                        "payload_sha256": (
                            "c" * 64
                        ),
                    }
                )
            )

            with self.assertRaises(
                RuntimeError
            ):
                coordinator.invoke(
                    request=invalid_request,
                    transport=(
                        SimulatedCodexTransport()
                    ),
                )

    def test_network_transport_not_authorized(
        self,
    ) -> None:
        class FakeNetworkTransport(
            SimulatedCodexTransport
        ):
            TRANSPORT_MODE = (
                "OPENAI_RESPONSES_API"
            )

        with TemporaryDirectory() as tmp:
            package_dir = (
                self._create_fixture(
                    Path(tmp)
                )
            )

            coordinator = (
                CodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                )
            )

            with self.assertRaises(
                RuntimeError
            ):
                coordinator.invoke(
                    request=self._request(),
                    transport=(
                        FakeNetworkTransport()
                    ),
                )


if __name__ == "__main__":
    unittest.main()
