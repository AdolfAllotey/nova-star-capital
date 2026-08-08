from __future__ import annotations

import unittest

from src.v2.audit_framework.providers.codex import (
    CodexAuditAdapter,
)
from src.v2.audit_framework.providers.contracts import (
    ProviderExecutionPolicy,
)


class ProviderAdapterTests(
    unittest.TestCase
):
    def test_codex_capabilities(
        self,
    ) -> None:
        adapter = CodexAuditAdapter()

        capabilities = (
            adapter.capabilities
        )

        self.assertEqual(
            capabilities.provider_id,
            "OPENAI_CODEX",
        )

        self.assertTrue(
            capabilities
            .supports_read_only_audit
        )

        self.assertFalse(
            capabilities
            .supports_automatic_remediation
        )

        self.assertFalse(
            capabilities
            .supports_live_execution
        )

    def test_execution_policy_is_safe(
        self,
    ) -> None:
        policy = ProviderExecutionPolicy(
            execution_mode="DRY_RUN",
            read_only=True,
            recommendation_only=True,
            automatic_remediation=False,
            allow_source_writes=False,
            allow_live_trading=False,
            allow_production_credentials=False,
            allow_network_side_effects=False,
            require_human_approval=True,
        )

        self.assertEqual(
            policy.execution_mode,
            "DRY_RUN",
        )

        self.assertTrue(
            policy.read_only
        )

        self.assertTrue(
            policy.require_human_approval
        )

        self.assertFalse(
            policy.allow_source_writes
        )

        self.assertFalse(
            policy.automatic_remediation
        )

    def test_execution_is_disabled(
        self,
    ) -> None:
        adapter = CodexAuditAdapter()

        with self.assertRaises(
            RuntimeError
        ):
            adapter.execute(
                payload=None  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
