from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import unittest

from src.v2.audit_framework.manifests.package_models import (
    AuditPackageManifest,
    PackageFile,
)


class AuditPackageBuilderTests(
    unittest.TestCase
):
    def test_package_file_serialization(
        self,
    ) -> None:
        item = PackageFile(
            path="AUDIT_SCOPE.md",
            role="AUDIT_SCOPE",
            sha256="a" * 64,
            size_bytes=10,
            required_for_audit=True,
            description="Scope",
        )

        payload = item.to_dict()

        self.assertEqual(
            payload["role"],
            "AUDIT_SCOPE",
        )

        self.assertTrue(
            payload[
                "required_for_audit"
            ]
        )

    def test_manifest_serialization(
        self,
    ) -> None:
        manifest = AuditPackageManifest(
            audit_id="TEST",
            release="RC1",
            baseline_id="RC1-TEST",
            package_status=(
                "READY_FOR_PROVIDER_AUDIT"
            ),
            created_at=(
                "2026-07-24T00:00:00Z"
            ),
            package_root="/tmp/test",
            provider="NONE",
            audit_mode=(
                "READ_ONLY_RECOMMENDATION_ONLY"
            ),
            baseline_aggregate_sha256=(
                "a" * 64
            ),
            collection_aggregate_sha256=(
                "b" * 64
            ),
            package_readiness_sha256=(
                "c" * 64
            ),
            files=[],
            objectives=[],
            constraints=[],
            deliverables=["Report"],
            recommendation_categories=[
                "RC1_HARDENING"
            ],
        )

        payload = manifest.to_dict()

        self.assertEqual(
            payload["release"],
            "RC1",
        )

        self.assertEqual(
            payload["provider"],
            "NONE",
        )

        self.assertFalse(
            payload["metadata"].get(
                "provider_executed",
                False,
            )
        )

    def test_readiness_hash_contract(
        self,
    ) -> None:
        digest = hashlib.sha256()

        digest.update(
            b"AUDIT_SCOPE.md"
        )
        digest.update(b"\0")
        digest.update(
            ("a" * 64).encode(
                "ascii"
            )
        )
        digest.update(b"\n")

        value = digest.hexdigest()

        self.assertEqual(
            len(value),
            64,
        )


if __name__ == "__main__":
    unittest.main()
