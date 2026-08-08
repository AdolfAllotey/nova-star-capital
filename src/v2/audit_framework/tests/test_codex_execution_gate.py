from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.v2.audit_framework.gates.codex import (
    CodexExecutionGate,
)


class CodexExecutionGateTests(
    unittest.TestCase
):
    def test_gate_identity(
        self,
    ) -> None:
        self.assertEqual(
            CodexExecutionGate.PROVIDER_ID,
            "OPENAI_CODEX",
        )

        self.assertEqual(
            CodexExecutionGate.APPROVAL_SCOPE,
            (
                "RC1_ENGINEERING_"
                "AUDIT_READ_ONLY"
            ),
        )

    def test_gate_id_is_unique(
        self,
    ) -> None:
        first = (
            CodexExecutionGate
            ._build_gate_id(
                audit_id="AUDIT-1",
                package_sha256="a" * 64,
                payload_sha256="b" * 64,
            )
        )

        second = (
            CodexExecutionGate
            ._build_gate_id(
                audit_id="AUDIT-1",
                package_sha256="a" * 64,
                payload_sha256="b" * 64,
            )
        )

        self.assertNotEqual(
            first,
            second,
        )

        self.assertTrue(
            first.startswith(
                "GATE-CODEX-"
            )
        )

    def test_expired_request_rejected(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            package = root / "package"
            package.mkdir()

            payload_dir = (
                package
                / "provider_payloads"
                / "openai_codex"
            )

            payload_dir.mkdir(
                parents=True
            )

            package_sha256 = "a" * 64

            payload_path = (
                payload_dir
                / "codex_audit_payload.json"
            )

            payload = {
                "package_readiness_sha256": (
                    package_sha256
                )
            }

            payload_path.write_text(
                json.dumps(
                    payload,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            import hashlib

            payload_sha256 = hashlib.sha256(
                payload_path.read_bytes()
            ).hexdigest()

            (
                package
                / "AUDIT_PACKAGE_MANIFEST.json"
            ).write_text(
                json.dumps(
                    {
                        "audit_id": "AUDIT-1",
                        "release": "RC1",
                        "package_readiness_sha256": (
                            package_sha256
                        ),
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            (
                package
                / "AUDIT_PACKAGE_READY.json"
            ).write_text(
                json.dumps(
                    {
                        "status": (
                            "READY_FOR_PROVIDER_AUDIT"
                        )
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            (
                payload_dir
                / "codex_preparation_report.json"
            ).write_text(
                json.dumps(
                    {
                        "payload_sha256": (
                            payload_sha256
                        )
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            gate = CodexExecutionGate(
                package_dir=package
            )

            expires = (
                datetime.now(
                    timezone.utc
                )
                - timedelta(
                    minutes=1
                )
            ).isoformat()

            with self.assertRaises(
                ValueError
            ):
                gate.create_request(
                    requested_by=(
                        "TEST_OPERATOR"
                    ),
                    expires_at=expires,
                )

    def test_parse_datetime_utc(
        self,
    ) -> None:
        value = (
            "2026-07-24T18:00:00+00:00"
        )

        parsed = (
            CodexExecutionGate
            ._parse_datetime(value)
        )

        self.assertEqual(
            parsed.tzinfo,
            timezone.utc,
        )


if __name__ == "__main__":
    unittest.main()
