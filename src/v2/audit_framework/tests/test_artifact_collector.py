from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import unittest

from src.v2.audit_framework.collectors.artifact_collector import (
    InstitutionalArtifactCollector,
)
from src.v2.audit_framework.collectors.artifact_definitions import (
    ArtifactDefinition,
)
from src.v2.audit_framework.core.enums import (
    ArtifactRole,
    AuditProvider,
    AuditStatus,
    AuditType,
)
from src.v2.audit_framework.core.exceptions import (
    ArtifactCollectionError,
)
from src.v2.audit_framework.core.models import (
    AuditRequest,
    AuditTarget,
)
from src.v2.audit_framework.core.utils import (
    utc_now_iso,
)


class ArtifactCollectorTests(
    unittest.TestCase
):
    def build_request(
        self,
    ) -> AuditRequest:
        return AuditRequest(
            audit_id="TEST-COLLECTION",
            audit_type=(
                AuditType.BASELINE_ENGINEERING
            ),
            provider=AuditProvider.NONE,
            status=AuditStatus.COLLECTING,
            target=AuditTarget(
                project="Nova Star Capital",
                release="RC1",
                baseline_id="TEST",
                baseline_status="FROZEN",
                aggregate_sha256=None,
                source_root="/tmp",
            ),
            created_at=utc_now_iso(),
            objectives=[],
            constraints=[],
            requested_deliverables=[],
        )

    def test_collect_required_artifact(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            source.write_text(
                '{"status":"PASS"}\n',
                encoding="utf-8",
            )

            package = (
                root
                / "audit-output"
                / "package"
            )

            definition = (
                ArtifactDefinition(
                    artifact_id="required",
                    role=(
                        ArtifactRole.RELEASE_GATE
                    ),
                    destination_name=(
                        "gate/source.json"
                    ),
                    required=True,
                    exact_paths=(source,),
                )
            )

            collector = (
                InstitutionalArtifactCollector(
                    (definition,)
                )
            )

            result = collector.collect(
                request=self.build_request(),
                package_dir=package,
            )

            self.assertEqual(
                result.status,
                "PASS",
            )

            self.assertEqual(
                result.required_collected,
                1,
            )

            copied = (
                package
                / "artifacts"
                / "gate"
                / "source.json"
            )

            self.assertTrue(
                copied.is_file()
            )

            expected_hash = (
                hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()
            )

            self.assertEqual(
                result.artifacts[0][
                    "sha256"
                ],
                expected_hash,
            )

    def test_missing_required_fails(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            definition = (
                ArtifactDefinition(
                    artifact_id="missing",
                    role=(
                        ArtifactRole.RELEASE_GATE
                    ),
                    destination_name=(
                        "missing.json"
                    ),
                    required=True,
                    exact_paths=(
                        root / "not-found.json",
                    ),
                )
            )

            collector = (
                InstitutionalArtifactCollector(
                    (definition,)
                )
            )

            with self.assertRaises(
                ArtifactCollectionError
            ):
                collector.collect(
                    request=(
                        self.build_request()
                    ),
                    package_dir=(
                        root / "package"
                    ),
                )

    def test_optional_missing_is_allowed(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            definition = (
                ArtifactDefinition(
                    artifact_id="optional",
                    role=ArtifactRole.OTHER,
                    destination_name=(
                        "optional"
                    ),
                    required=False,
                    exact_paths=(
                        root / "not-found.txt",
                    ),
                )
            )

            collector = (
                InstitutionalArtifactCollector(
                    (definition,)
                )
            )

            result = collector.collect(
                request=self.build_request(),
                package_dir=(
                    root / "package"
                ),
            )

            self.assertEqual(
                result.status,
                "PASS",
            )

            self.assertEqual(
                result.total_collected,
                0,
            )

            self.assertEqual(
                len(result.issues),
                1,
            )

            self.assertFalse(
                result.issues[0].blocking
            )


if __name__ == "__main__":
    unittest.main()
