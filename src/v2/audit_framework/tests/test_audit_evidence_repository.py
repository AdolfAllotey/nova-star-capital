from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import unittest

from src.v2.audit_framework.evidence import (
    ImmutableAuditEvidenceRepository,
)


class AuditEvidenceRepositoryTests(
    unittest.TestCase
):
    @staticmethod
    def _sha(
        payload: object,
    ) -> str:
        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    @classmethod
    def _payloads(
        cls,
    ) -> tuple[
        dict[str, object],
        dict[str, object],
    ]:
        request = {
            "model": "SIMULATED",
            "input": "Audit evidence",
            "store": False,
        }

        response = {
            "id": None,
            "status": "SIMULATED_SUCCESS",
            "output_text": (
                "No production execution."
            ),
        }

        return request, response

    @classmethod
    def _persist(
        cls,
        repository: (
            ImmutableAuditEvidenceRepository
        ),
    ):
        request, response = (
            cls._payloads()
        )

        return repository.persist(
            provider_id="OPENAI_CODEX",
            audit_id="AUDIT-TEST",
            gate_id=(
                "GATE-CODEX-TEST-001"
            ),
            invocation_id=(
                "INVOCATION-CODEX-TEST-001"
            ),
            package_readiness_sha256=(
                "a" * 64
            ),
            payload_sha256=(
                "b" * 64
            ),
            request_sha256=(
                cls._sha(request)
            ),
            response_sha256=(
                cls._sha(response)
            ),
            provider_response_id=None,
            model="SIMULATED",
            transport_mode=(
                "SIMULATED_NO_NETWORK"
            ),
            provider_executed=False,
            network_invocation_performed=False,
            raw_request=request,
            raw_response=response,
            output_text=(
                "No production execution."
            ),
            metadata={
                "test_fixture": True,
            },
        )

    def test_persist_and_verify(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            result = self._persist(
                repository
            )

            self.assertEqual(
                result.status,
                "IMMUTABLE_EVIDENCE_STORED",
            )

            self.assertFalse(
                result.existing_record_reused
            )

            verification = (
                repository.verify(
                    evidence_dir=Path(
                        result.evidence_dir
                    )
                )
            )

            self.assertEqual(
                verification["status"],
                "VERIFIED",
            )

            self.assertTrue(
                verification[
                    "aggregate_match"
                ]
            )

    def test_identical_evidence_reused(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            first = self._persist(
                repository
            )

            second = self._persist(
                repository
            )

            self.assertEqual(
                first.evidence_id,
                second.evidence_id,
            )

            self.assertTrue(
                second.existing_record_reused
            )

            self.assertEqual(
                second.status,
                "IMMUTABLE_EVIDENCE_REUSED",
            )

    def test_request_hash_mismatch_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            request, response = (
                self._payloads()
            )

            with self.assertRaises(
                ValueError
            ):
                repository.persist(
                    provider_id=(
                        "OPENAI_CODEX"
                    ),
                    audit_id="AUDIT-TEST",
                    gate_id=(
                        "GATE-CODEX-TEST-001"
                    ),
                    invocation_id=(
                        "INVOCATION-CODEX-TEST-001"
                    ),
                    package_readiness_sha256=(
                        "a" * 64
                    ),
                    payload_sha256=(
                        "b" * 64
                    ),
                    request_sha256=(
                        "c" * 64
                    ),
                    response_sha256=(
                        self._sha(response)
                    ),
                    provider_response_id=None,
                    model="SIMULATED",
                    transport_mode=(
                        "SIMULATED_NO_NETWORK"
                    ),
                    provider_executed=False,
                    network_invocation_performed=False,
                    raw_request=request,
                    raw_response=response,
                    output_text="Output",
                )

    def test_response_hash_mismatch_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            request, response = (
                self._payloads()
            )

            with self.assertRaises(
                ValueError
            ):
                repository.persist(
                    provider_id=(
                        "OPENAI_CODEX"
                    ),
                    audit_id="AUDIT-TEST",
                    gate_id=(
                        "GATE-CODEX-TEST-001"
                    ),
                    invocation_id=(
                        "INVOCATION-CODEX-TEST-001"
                    ),
                    package_readiness_sha256=(
                        "a" * 64
                    ),
                    payload_sha256=(
                        "b" * 64
                    ),
                    request_sha256=(
                        self._sha(request)
                    ),
                    response_sha256=(
                        "d" * 64
                    ),
                    provider_response_id=None,
                    model="SIMULATED",
                    transport_mode=(
                        "SIMULATED_NO_NETWORK"
                    ),
                    provider_executed=False,
                    network_invocation_performed=False,
                    raw_request=request,
                    raw_response=response,
                    output_text="Output",
                )

    def test_tampering_detected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            result = self._persist(
                repository
            )

            evidence_dir = Path(
                result.evidence_dir
            )

            response_path = (
                evidence_dir
                / "raw_response.json"
            )

            response_path.chmod(0o640)

            response_path.write_text(
                '{"tampered":true}',
                encoding="utf-8",
            )

            verification = (
                repository.verify(
                    evidence_dir=(
                        evidence_dir
                    )
                )
            )

            self.assertEqual(
                verification["status"],
                "FAILED",
            )

            statuses = {
                item["status"]
                for item in verification[
                    "findings"
                ]
            }

            self.assertIn(
                "HASH_MISMATCH",
                statuses,
            )

    def test_files_are_read_only(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            repository = (
                ImmutableAuditEvidenceRepository(
                    root_dir=Path(tmp)
                )
            )

            result = self._persist(
                repository
            )

            evidence_dir = Path(
                result.evidence_dir
            )

            for path in evidence_dir.iterdir():
                if path.is_file():
                    mode = (
                        path.stat().st_mode
                        & 0o777
                    )

                    self.assertEqual(
                        mode,
                        0o440,
                    )


if __name__ == "__main__":
    unittest.main()
