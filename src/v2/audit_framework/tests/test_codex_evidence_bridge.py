from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.v2.audit_framework.evidence import (
    ImmutableAuditEvidenceRepository,
)
from src.v2.audit_framework.integrations import (
    CodexEvidenceCaptureBridge,
)
from src.v2.audit_framework.transports import (
    ProviderTransportRequest,
    SimulatedCodexTransport,
)


class CodexEvidenceCaptureBridgeTests(
    unittest.TestCase
):
    PACKAGE_SHA = "a" * 64
    PAYLOAD_SHA = "b" * 64

    @classmethod
    def _request(
        cls,
    ) -> ProviderTransportRequest:
        return ProviderTransportRequest(
            schema_version="1.0",
            invocation_id=(
                "INVOCATION-CODEX-BRIDGE-001"
            ),
            provider_id="OPENAI_CODEX",
            audit_id="AUDIT-BRIDGE-TEST",
            gate_id=(
                "GATE-CODEX-BRIDGE-001"
            ),
            package_readiness_sha256=(
                cls.PACKAGE_SHA
            ),
            payload_sha256=(
                cls.PAYLOAD_SHA
            ),
            model="SIMULATED",
            instructions=(
                "Perform a simulated read-only audit."
            ),
            input_text=(
                "Simulated evidence payload."
            ),
            max_output_tokens=1000,
            store=False,
            tools_enabled=False,
            network_invocation_authorized=False,
            metadata={
                "test_fixture": True,
                "automatic_remediation": False,
            },
        )

    def test_capture_and_verify(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            bridge = (
                CodexEvidenceCaptureBridge(
                    repository=repository
                )
            )

            request = self._request()

            result = (
                SimulatedCodexTransport()
                .invoke(request)
            )

            persistence = bridge.capture(
                request=request,
                result=result,
                metadata={
                    "test_name": (
                        "capture_and_verify"
                    ),
                },
            )

            self.assertEqual(
                persistence.status,
                "IMMUTABLE_EVIDENCE_STORED",
            )

            self.assertFalse(
                persistence
                .existing_record_reused
            )

            verification = (
                repository.verify(
                    evidence_dir=Path(
                        persistence.evidence_dir
                    )
                )
            )

            self.assertEqual(
                verification["status"],
                "VERIFIED",
            )

    def test_identical_capture_is_idempotent(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            bridge = (
                CodexEvidenceCaptureBridge(
                    repository=repository
                )
            )

            request = self._request()

            result = (
                SimulatedCodexTransport()
                .invoke(request)
            )

            first = bridge.capture(
                request=request,
                result=result,
            )

            second = bridge.capture(
                request=request,
                result=result,
            )

            self.assertEqual(
                first.evidence_id,
                second.evidence_id,
            )

            self.assertTrue(
                second
                .existing_record_reused
            )

            self.assertEqual(
                second.status,
                "IMMUTABLE_EVIDENCE_REUSED",
            )

    def test_provider_mismatch_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            bridge = (
                CodexEvidenceCaptureBridge(
                    repository=repository
                )
            )

            request = self._request()

            invalid_request = replace(
                request,
                provider_id=(
                    "INVALID_PROVIDER"
                ),
            )

            result = (
                SimulatedCodexTransport()
                .invoke(request)
            )

            with self.assertRaises(
                RuntimeError
            ):
                bridge.capture(
                    request=invalid_request,
                    result=result,
                )

    def test_invocation_binding_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            bridge = (
                CodexEvidenceCaptureBridge(
                    repository=repository
                )
            )

            request = self._request()

            result = (
                SimulatedCodexTransport()
                .invoke(request)
            )

            invalid_request = replace(
                request,
                invocation_id=(
                    "INVOCATION-CODEX-BRIDGE-999"
                ),
            )

            with self.assertRaises(
                RuntimeError
            ):
                bridge.capture(
                    request=invalid_request,
                    result=result,
                )

    def test_transport_response_hash_contract(
        self,
    ) -> None:
        request = self._request()

        result = (
            SimulatedCodexTransport()
            .invoke(request)
        )

        payload = {
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

        import hashlib
        import json

        observed = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(
            observed,
            result.response_sha256,
        )

    def test_no_provider_execution_recorded(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            bridge = (
                CodexEvidenceCaptureBridge(
                    repository=repository
                )
            )

            request = self._request()

            result = (
                SimulatedCodexTransport()
                .invoke(request)
            )

            persistence = bridge.capture(
                request=request,
                result=result,
            )

            manifest_path = (
                Path(
                    persistence.evidence_dir
                )
                / "evidence_manifest.json"
            )

            manifest = __import__(
                "json"
            ).loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertFalse(
                manifest[
                    "provider_executed"
                ]
            )

            self.assertFalse(
                manifest[
                    "network_invocation_performed"
                ]
            )

            self.assertFalse(
                manifest["metadata"][
                    "automatic_remediation"
                ]
            )


if __name__ == "__main__":
    unittest.main()
