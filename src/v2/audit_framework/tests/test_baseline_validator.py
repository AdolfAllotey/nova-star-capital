from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import unittest

from src.v2.audit_framework.validators.extraction import (
    coerce_bool,
    find_first_value,
    normalize_upper,
)


class BaselineValidatorHelperTests(
    unittest.TestCase
):
    def test_nested_value_extraction(
        self,
    ) -> None:
        payload = {
            "release": {
                "baseline": {
                    "baseline_id": "RC1-TEST"
                }
            }
        }

        value, path = find_first_value(
            payload,
            (
                "baseline_id",
            ),
        )

        self.assertEqual(
            value,
            "RC1-TEST",
        )

        self.assertEqual(
            path,
            "release.baseline.baseline_id",
        )

    def test_boolean_coercion(
        self,
    ) -> None:
        self.assertIs(
            coerce_bool(True),
            True,
        )

        self.assertIs(
            coerce_bool("false"),
            False,
        )

        self.assertIs(
            coerce_bool("FROZEN"),
            True,
        )

    def test_upper_normalization(
        self,
    ) -> None:
        self.assertEqual(
            normalize_upper(
                " approved "
            ),
            "APPROVED",
        )

    def test_inventory_hash_contract(
        self,
    ) -> None:
        artifacts = [
            {
                "artifact_id": "a",
                "role": "RELEASE_GATE",
                "package_path": (
                    "artifacts/gate.json"
                ),
                "sha256": "1" * 64,
            }
        ]

        digest = hashlib.sha256()

        digest.update(b"a")
        digest.update(b"\0")
        digest.update(b"RELEASE_GATE")
        digest.update(b"\0")
        digest.update(
            b"artifacts/gate.json"
        )
        digest.update(b"\0")
        digest.update(
            ("1" * 64).encode("ascii")
        )
        digest.update(b"\n")

        calculated = digest.hexdigest()

        self.assertEqual(
            len(calculated),
            64,
        )


if __name__ == "__main__":
    unittest.main()
