from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.v2.audit_framework.evidence import (
    ImmutableAuditEvidenceRepository,
)
from src.v2.audit_framework.invocations import (
    EvidenceAwareCodexInvocationCoordinator,
)
from src.v2.audit_framework.transports import (
    ProviderTransportRequest,
    SimulatedCodexTransport,
)


class EvidenceAwareCodexInvocationCoordinatorTests(
    unittest.TestCase
):
    PACKAGE_SHA = "a" * 64
    PAYLOAD_SHA = "b" * 64
    GATE_ID = (
        "GATE-CODEX-EVIDENCE-TEST-001"
    )

    @classmethod
    def _create_fixture(
        cls,
        root: Path,
    ) -> tuple[Path, Path]:
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

        gate_request = {
            "schema_version": "1.0",
            "gate_id": cls.GATE_ID,
            "provider_id": "OPENAI_CODEX",
            "audit_id": (
                "AUDIT-EVIDENCE-TEST"
            ),
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

        gate_state = {
            "schema_version": "1.0",
            "gate_id": cls.GATE_ID,
            "provider_id": "OPENAI_CODEX",
            "audit_id": (
                "AUDIT-EVIDENCE-TEST"
            ),
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
                gate_request,
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
                gate_state,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        evidence_root = (
            root / "evidence"
        )

        return package_dir, evidence_root

    @classmethod
    def _request(
        cls,
        *,
        invocation_id: str = (
            "INVOCATION-CODEX-EVIDENCE-001"
        ),
    ) -> ProviderTransportRequest:
        return ProviderTransportRequest(
            schema_version="1.0",
            invocation_id=invocation_id,
            provider_id="OPENAI_CODEX",
            audit_id=(
                "AUDIT-EVIDENCE-TEST"
            ),
            gate_id=cls.GATE_ID,
            package_readiness_sha256=(
                cls.PACKAGE_SHA
            ),
            payload_sha256=(
                cls.PAYLOAD_SHA
            ),
            model="SIMULATED",
            instructions=(
                "Perform a simulated "
                "read-only audit."
            ),
            input_text=(
                "Test immutable evidence."
            ),
            max_output_tokens=1000,
            store=False,
            tools_enabled=False,
            network_invocation_authorized=False,
            metadata={
                "automatic_remediation": False,
            },
        )

    def test_atomic_simulated_execution(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            (
                package_dir,
                evidence_root,
            ) = self._create_fixture(root)

            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=evidence_root
                )
            )

            coordinator = (
                EvidenceAwareCodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                    evidence_repository=repository,
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

            invocation_dir = (
                coordinator.invocations_dir
                / receipt.invocation_id
            )

            binding_path = (
                invocation_dir
                / "invocation_evidence_binding.json"
            )

            self.assertTrue(
                binding_path.is_file()
            )

            binding = json.loads(
                binding_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                binding[
                    "verification_status"
                ],
                "VERIFIED",
            )

            self.assertTrue(
                binding["metadata"][
                    "evidence_verified"
                ]
            )

            evidence_dir = Path(
                binding["evidence_dir"]
            )

            verification = repository.verify(
                evidence_dir=evidence_dir
            )

            self.assertEqual(
                verification["status"],
                "VERIFIED",
            )

    def test_evidence_created_before_receipt(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            (
                package_dir,
                evidence_root,
            ) = self._create_fixture(root)

            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=evidence_root
                )
            )

            coordinator = (
                EvidenceAwareCodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                    evidence_repository=repository,
                )
            )

            receipt = coordinator.invoke(
                request=self._request(),
                transport=(
                    SimulatedCodexTransport()
                ),
            )

            invocation_dir = (
                coordinator.invocations_dir
                / receipt.invocation_id
            )

            binding = json.loads(
                (
                    invocation_dir
                    / "invocation_evidence_binding.json"
                ).read_text(
                    encoding="utf-8"
                )
            )

            evidence_manifest = (
                Path(binding["evidence_dir"])
                / "evidence_manifest.json"
            )

            receipt_path = (
                invocation_dir
                / "invocation_receipt.json"
            )

            self.assertTrue(
                evidence_manifest.is_file()
            )

            self.assertTrue(
                receipt_path.is_file()
            )

            self.assertLessEqual(
                evidence_manifest
                .stat()
                .st_mtime_ns,
                receipt_path
                .stat()
                .st_mtime_ns,
            )

    def test_second_invocation_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            (
                package_dir,
                evidence_root,
            ) = self._create_fixture(root)

            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=evidence_root
                )
            )

            coordinator = (
                EvidenceAwareCodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                    evidence_repository=repository,
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
                            "INVOCATION-CODEX-"
                            "EVIDENCE-002"
                        ),
                    ),
                    transport=(
                        SimulatedCodexTransport()
                    ),
                )

    def test_transport_failure_consumes_gate(
        self,
    ) -> None:
        class FailingTransport(
            SimulatedCodexTransport
        ):
            def invoke(self, request):
                raise RuntimeError(
                    "Simulated transport failure."
                )

        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            (
                package_dir,
                evidence_root,
            ) = self._create_fixture(root)

            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=evidence_root
                )
            )

            coordinator = (
                EvidenceAwareCodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                    evidence_repository=repository,
                )
            )

            with self.assertRaises(
                RuntimeError
            ):
                coordinator.invoke(
                    request=self._request(),
                    transport=FailingTransport(),
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
                "CONSUMED_AFTER_FAILURE",
            )

            self.assertFalse(
                state["provider_executed"]
            )

    def test_evidence_failure_consumes_gate(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            (
                package_dir,
                evidence_root,
            ) = self._create_fixture(root)

            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=evidence_root
                )
            )

            coordinator = (
                EvidenceAwareCodexInvocationCoordinator(
                    package_dir=package_dir,
                    gate_id=self.GATE_ID,
                    evidence_repository=repository,
                )
            )

            class FailingBridge:
                def capture(self, **kwargs):
                    raise RuntimeError(
                        "Simulated evidence failure."
                    )

            coordinator.evidence_bridge = (
                FailingBridge()
            )

            with self.assertRaises(
                RuntimeError
            ):
                coordinator.invoke(
                    request=self._request(),
                    transport=(
                        SimulatedCodexTransport()
                    ),
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
                "CONSUMED_AFTER_FAILURE",
            )

            self.assertFalse(
                state["provider_executed"]
            )


if __name__ == "__main__":
    unittest.main()
