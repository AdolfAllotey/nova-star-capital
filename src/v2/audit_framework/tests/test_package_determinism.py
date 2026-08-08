from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import unittest

from src.v2.audit_framework.manifests.audit_package_builder import (
    RC1AuditPackageBuilder,
)


class PackageDeterminismTests(
    unittest.TestCase
):
    def test_ready_file_excluded_from_hash(
        self,
    ) -> None:
        self.assertIn(
            "AUDIT_PACKAGE_READY.json",
            (
                RC1AuditPackageBuilder
                .EXCLUDED_FROM_READINESS_HASH
            ),
        )

    def test_manifest_excluded_from_hash(
        self,
    ) -> None:
        self.assertIn(
            "AUDIT_PACKAGE_MANIFEST.json",
            (
                RC1AuditPackageBuilder
                .EXCLUDED_FROM_READINESS_HASH
            ),
        )

    def test_checksum_file_excluded_from_hash(
        self,
    ) -> None:
        self.assertIn(
            "PACKAGE_CHECKSUMS.sha256",
            (
                RC1AuditPackageBuilder
                .EXCLUDED_FROM_READINESS_HASH
            ),
        )

    def test_hash_stable_when_excluded_file_changes(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            stable_path = root / "stable.txt"
            volatile_path = (
                root
                / "AUDIT_PACKAGE_READY.json"
            )

            stable_path.write_text(
                "stable-content",
                encoding="utf-8",
            )

            volatile_path.write_text(
                '{"last_verified_at":"one"}',
                encoding="utf-8",
            )

            def calculate() -> str:
                digest = hashlib.sha256()

                files = sorted(
                    [
                        path
                        for path
                        in root.rglob("*")
                        if path.is_file()
                        and path.name
                        not in (
                            RC1AuditPackageBuilder
                            .EXCLUDED_FROM_READINESS_HASH
                        )
                    ],
                    key=lambda value: str(
                        value.relative_to(root)
                    ),
                )

                for path in files:
                    relative = str(
                        path.relative_to(root)
                    )

                    checksum = hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest()

                    digest.update(
                        relative.encode(
                            "utf-8"
                        )
                    )
                    digest.update(b"\0")
                    digest.update(
                        checksum.encode(
                            "ascii"
                        )
                    )
                    digest.update(b"\n")

                return digest.hexdigest()

            first = calculate()

            volatile_path.write_text(
                '{"last_verified_at":"two"}',
                encoding="utf-8",
            )

            second = calculate()

            self.assertEqual(
                first,
                second,
            )


if __name__ == "__main__":
    unittest.main()
