from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.v2.audit_framework.evidence import (
    ImmutableAuditEvidenceRepository,
)
from src.v2.audit_framework.integrations import (
    CodexRegistryIntegrator,
)
from src.v2.audit_framework.invocations import (
    EvidenceAwareCodexInvocationCoordinator,
)
from src.v2.audit_framework.transports import (
    ProviderTransportRequest,
    SimulatedCodexTransport,
)


class CodexRegistryIntegratorTests(
    unittest.TestCase
):
    PACKAGE_SHA = "a" * 64
    PAYLOAD_SHA = "b" * 64
    GATE_ID = (
        "GATE-CODEX-REGISTRY-TEST"
    )
    AUDIT_ID = (
        "AUDIT-REGISTRY-TEST"
    )

    def _fixture(
        self,
        root: Path,
    ):
        package_dir = root / "package"

        gate_dir = (
            package_dir
            / "execution_gates"
            / "openai_codex"
            / self.GATE_ID
        )

        gate_dir.mkdir(
            parents=True
        )

        gate_request = {
            "schema_version": "1.0",
            "gate_id": self.GATE_ID,
            "provider_id": "OPENAI_CODEX",
            "audit_id": self.AUDIT_ID,
            "release": "RC1",
            "package_readiness_sha256": (
                self.PACKAGE_SHA
            ),
            "payload_sha256": (
                self.PAYLOAD_SHA
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
            "gate_id": self.GATE_ID,
            "provider_id": "OPENAI_CODEX",
            "audit_id": self.AUDIT_ID,
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

        registry_path = (
            root
            / "registry"
            / "audit_framework_registry.json"
        )

        history_path = (
            root
            / "registry"
            / "audit_framework_history.jsonl"
        )

        registry_path.parent.mkdir(
            parents=True
        )

        registry = {
            "schema_version": "1.0",
            "status": "FOUNDATION_READY",
            "updated_at": (
                "2026-07-25T00:00:00+00:00"
            ),
            "capabilities": {},
            "latest_audit_package": {
                "audit_id": self.AUDIT_ID,
                "package_readiness_sha256": (
                    self.PACKAGE_SHA
                ),
            },
            "latest_execution_gate": {
                "gate_id": self.GATE_ID,
                "provider_id": "OPENAI_CODEX",
                "payload_sha256": (
                    self.PAYLOAD_SHA
                ),
            },
            "latest_codex_invocation": None,
            "latest_codex_transport": None,
            "latest_audit_evidence": None,
        }

        registry_path.write_text(
            json.dumps(
                registry,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        repository = (
            ImmutableAuditEvidenceRepository(
                root_dir=root / "evidence"
            )
        )

        coordinator = (
            EvidenceAwareCodexInvocationCoordinator(
                package_dir=package_dir,
                gate_id=self.GATE_ID,
                evidence_repository=repository,
            )
        )

        request = ProviderTransportRequest(
            schema_version="1.0",
            invocation_id=(
                "INVOCATION-CODEX-REGISTRY-001"
            ),
            provider_id="OPENAI_CODEX",
            audit_id=self.AUDIT_ID,
            gate_id=self.GATE_ID,
            package_readiness_sha256=(
                self.PACKAGE_SHA
            ),
            payload_sha256=(
                self.PAYLOAD_SHA
            ),
            model="SIMULATED",
            instructions=(
                "Perform simulated audit."
            ),
            input_text=(
                "Registry integration fixture."
            ),
            max_output_tokens=1000,
            store=False,
            tools_enabled=False,
            network_invocation_authorized=False,
            metadata={},
        )

        transport = SimulatedCodexTransport()

        receipt = coordinator.invoke(
            request=request,
            transport=transport,
        )

        invocation_dir = (
            coordinator.invocations_dir
            / request.invocation_id
        )

        transport_result = json.loads(
            (
                invocation_dir
                / "transport_result.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        binding = json.loads(
            (
                invocation_dir
                / "invocation_evidence_binding.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        evidence_dir = Path(
            binding["evidence_dir"]
        )

        manifest = json.loads(
            (
                evidence_dir
                / "evidence_manifest.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        verification = repository.verify(
            evidence_dir=evidence_dir
        )

        integrator = CodexRegistryIntegrator(
            registry_path=registry_path,
            history_path=history_path,
        )

        return {
            "registry_path": registry_path,
            "history_path": history_path,
            "receipt": receipt,
            "transport_result": (
                transport_result
            ),
            "binding": binding,
            "manifest": manifest,
            "verification": verification,
            "integrator": integrator,
        }

    def test_successful_registration(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            fixture = self._fixture(
                Path(tmp)
            )

            result = fixture[
                "integrator"
            ].register(
                receipt=fixture["receipt"],
                transport_result=fixture[
                    "transport_result"
                ],
                evidence_binding=fixture[
                    "binding"
                ],
                evidence_manifest=fixture[
                    "manifest"
                ],
                evidence_verification=fixture[
                    "verification"
                ],
            )

            self.assertEqual(
                result["status"],
                "REGISTERED",
            )

            registry = json.loads(
                fixture[
                    "registry_path"
                ].read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                registry[
                    "latest_codex_invocation"
                ]["status"],
                "CONSUMED_SIMULATED",
            )

            self.assertEqual(
                registry[
                    "latest_audit_evidence"
                ]["verification_status"],
                "VERIFIED",
            )

            self.assertEqual(
                registry[
                    "latest_audit_evidence"
                ]["status"],
                "IMMUTABLE_EVIDENCE_STORED",
            )

            self.assertEqual(
                registry["capabilities"][
                    "codex_registry_integration"
                ],
                "READY",
            )

    def test_history_event_written(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            fixture = self._fixture(
                Path(tmp)
            )

            fixture[
                "integrator"
            ].register(
                receipt=fixture["receipt"],
                transport_result=fixture[
                    "transport_result"
                ],
                evidence_binding=fixture[
                    "binding"
                ],
                evidence_manifest=fixture[
                    "manifest"
                ],
                evidence_verification=fixture[
                    "verification"
                ],
            )

            lines = fixture[
                "history_path"
            ].read_text(
                encoding="utf-8"
            ).splitlines()

            self.assertEqual(
                len(lines),
                1,
            )

            event = json.loads(
                lines[0]
            )

            self.assertEqual(
                event["event"],
                "CODEX_INVOCATION_REGISTERED",
            )

            self.assertEqual(
                event[
                    "verification_status"
                ],
                "VERIFIED",
            )

            self.assertEqual(
                event[
                    "evidence_status"
                ],
                "IMMUTABLE_EVIDENCE_STORED",
            )

    def test_unverified_evidence_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            fixture = self._fixture(
                Path(tmp)
            )

            before = fixture[
                "registry_path"
            ].read_text(
                encoding="utf-8"
            )

            with self.assertRaises(
                RuntimeError
            ):
                fixture[
                    "integrator"
                ].register(
                    receipt=fixture[
                        "receipt"
                    ],
                    transport_result=fixture[
                        "transport_result"
                    ],
                    evidence_binding=fixture[
                        "binding"
                    ],
                    evidence_manifest=fixture[
                        "manifest"
                    ],
                    evidence_verification={
                        "status": "FAILED",
                    },
                )

            after = fixture[
                "registry_path"
            ].read_text(
                encoding="utf-8"
            )

            self.assertEqual(
                before,
                after,
            )

    def test_response_sha_mismatch_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            fixture = self._fixture(
                Path(tmp)
            )

            invalid_transport = {
                **fixture[
                    "transport_result"
                ],
                "response_sha256": (
                    "c" * 64
                ),
            }

            with self.assertRaises(
                RuntimeError
            ):
                fixture[
                    "integrator"
                ].register(
                    receipt=fixture[
                        "receipt"
                    ],
                    transport_result=(
                        invalid_transport
                    ),
                    evidence_binding=fixture[
                        "binding"
                    ],
                    evidence_manifest=fixture[
                        "manifest"
                    ],
                    evidence_verification=fixture[
                        "verification"
                    ],
                )

    def test_wrong_registry_gate_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            fixture = self._fixture(
                Path(tmp)
            )

            registry = json.loads(
                fixture[
                    "registry_path"
                ].read_text(
                    encoding="utf-8"
                )
            )

            registry[
                "latest_execution_gate"
            ]["gate_id"] = (
                "GATE-CODEX-WRONG"
            )

            fixture[
                "registry_path"
            ].write_text(
                json.dumps(
                    registry,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                RuntimeError
            ):
                fixture[
                    "integrator"
                ].register(
                    receipt=fixture[
                        "receipt"
                    ],
                    transport_result=fixture[
                        "transport_result"
                    ],
                    evidence_binding=fixture[
                        "binding"
                    ],
                    evidence_manifest=fixture[
                        "manifest"
                    ],
                    evidence_verification=fixture[
                        "verification"
                    ],
                )


if __name__ == "__main__":
    unittest.main()
