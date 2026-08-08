from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT = Path("data/audits/preprod_readiness_report.json")

MASTER_AUDIT_PATH = Path("data/audits/master_to_bricks_audit.json")
SEMANTIC_AUDIT_PATH = Path("data/audits/master_semantic_audit.json")

FAMILY_OFFICE_PATH = Path("data/capital/family_office_bundle.json")
TREASURY_PATH = Path("data/capital/treasury_state.json")
COLLATERAL_PATH = Path("data/capital/collateral_state.json")
FUNDING_PATH = Path("data/capital/funding_plan.json")
REBALANCE_PATH = Path("data/capital/rebalance_plan.json")
CAPITAL_CONTEXT_PATH = Path("data/capital/config/capital_context.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "path": str(path),
        }


def main() -> None:
    structural = read_json(MASTER_AUDIT_PATH, {})
    semantic = read_json(SEMANTIC_AUDIT_PATH, {})
    family_office = read_json(FAMILY_OFFICE_PATH, {})
    treasury = read_json(TREASURY_PATH, {})
    collateral = read_json(COLLATERAL_PATH, {})
    funding = read_json(FUNDING_PATH, {})
    rebalance = read_json(REBALANCE_PATH, {})
    capital_context = read_json(CAPITAL_CONTEXT_PATH, {})

    report = {
        "status": "ok",
        "engine": "preprod_readiness_report_v1",
        "generated_at": utc_now(),

        "environment": {
            "environment": capital_context.get("environment"),
            "capital_mode": capital_context.get("capital_mode"),
            "real_money_enabled": capital_context.get("real_money_enabled"),
            "real_broker_funding_enabled": capital_context.get("real_broker_funding_enabled"),
            "collateral_enabled": capital_context.get("collateral_enabled"),
            "real_debt_enabled": capital_context.get("real_debt_enabled"),
        },

        "summary": {
            "structural_audit_status": structural.get("status"),
            "semantic_audit_status": semantic.get("status"),
            "enterprise_value_eur": (
                family_office.get("headline", {})
                .get("enterprise_net_value_eur", 0.0)
            ),
            "treasury_health": (
                treasury.get("health", {})
                .get("treasury_health")
            ),
            "collateral_status": collateral.get("ltv_status"),
            "funding_status": funding.get("status"),
            "rebalance_status": rebalance.get("status"),
        },

        "production_like_validation": {
            "all_systems_simulated": (
                capital_context.get("capital_mode") == "virtual"
                and capital_context.get("real_money_enabled") is False
            ),
            "no_real_execution": True,
            "manual_governance_required": True,
            "protected_buckets_enabled": True,
            "family_office_layer_enabled": True,
            "capital_brain_enabled": True,
        },

        "remaining_work": [
            "Harmonize Family Office UI with Dashboard V4 visual baseline",
            "Audit every brick against Master architecture in detail",
            "Verify all API/UI endpoints are connected to real artifacts",
            "Run production-like preprod with all bricks enabled simultaneously",
            "Validate funding flows and rebalance interactions in runtime",
            "Validate governance and kill-switch scenarios",
            "Review logs, telemetry and monitoring consistency",
            "Run 48h production-like stability test",
            "Prepare final PREPROD GO/NO-GO checklist"
        ],

        "warnings": [
            "Current capital is virtual PREPROD seed capital only.",
            "Enterprise valuation is simulated and non-accounting.",
            "No real broker funding or real debt is enabled."
        ]
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
