from __future__ import annotations

import unittest

from src.v2.audit_framework.core.constants import (
    AUDIT_FRAMEWORK_NAME,
    AUDIT_FRAMEWORK_SCHEMA_VERSION,
    AUDIT_FRAMEWORK_VERSION,
)
from src.v2.audit_framework.core.enums import (
    AuditProvider,
    AuditStatus,
    AuditType,
)
from src.v2.audit_framework.core.models import (
    AuditRequest,
    AuditTarget,
    EngineeringScore,
)
from src.v2.audit_framework.core.utils import (
    utc_now_iso,
)


class AuditFrameworkFoundationTests(
    unittest.TestCase
):
    def test_framework_identity(self) -> None:
        self.assertEqual(
            AUDIT_FRAMEWORK_NAME,
            "NSC_AUDIT_FRAMEWORK",
        )

        self.assertEqual(
            AUDIT_FRAMEWORK_VERSION,
            "1.0.0",
        )

        self.assertEqual(
            AUDIT_FRAMEWORK_SCHEMA_VERSION,
            "1.0",
        )

    def test_audit_request_serialization(
        self,
    ) -> None:
        target = AuditTarget(
            project="Nova Star Capital",
            release="RC1",
            baseline_id=(
                "RC1-20260724T142844Z"
            ),
            baseline_status="FROZEN",
            aggregate_sha256=None,
            source_root="/opt/nsc/app",
        )

        request = AuditRequest(
            audit_id="TEST-RC1",
            audit_type=(
                AuditType.BASELINE_ENGINEERING
            ),
            provider=AuditProvider.NONE,
            status=AuditStatus.CREATED,
            target=target,
            created_at=utc_now_iso(),
            objectives=[
                "Validate foundation",
            ],
            constraints=[
                "No code modification",
            ],
            requested_deliverables=[
                "Foundation result",
            ],
        )

        payload = request.to_dict()

        self.assertEqual(
            payload["audit_type"],
            "BASELINE_ENGINEERING",
        )

        self.assertEqual(
            payload["provider"],
            "NONE",
        )

        self.assertEqual(
            payload["status"],
            "CREATED",
        )

        self.assertEqual(
            payload["target"]["release"],
            "RC1",
        )

    def test_engineering_score_validation(
        self,
    ) -> None:
        score = EngineeringScore(
            architecture=90,
            security=91,
            performance=92,
            maintainability=93,
            testing=94,
            documentation=95,
            observability=96,
            governance=100,
            overall=94,
        )

        payload = score.to_dict()

        self.assertEqual(
            payload["governance"],
            100,
        )

    def test_invalid_engineering_score(
        self,
    ) -> None:
        score = EngineeringScore(
            architecture=101,
            security=90,
            performance=90,
            maintainability=90,
            testing=90,
            documentation=90,
            observability=90,
            governance=90,
            overall=90,
        )

        with self.assertRaises(
            ValueError
        ):
            score.validate()


if __name__ == "__main__":
    unittest.main()
