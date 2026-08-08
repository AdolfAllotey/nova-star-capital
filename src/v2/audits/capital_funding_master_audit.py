from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
OUTPUT = DATA / "audits" / "capital_funding_master_audit.json"

CAPITAL_CONTEXT = DATA / "capital/config/capital_context.json"
CAPITAL_POLICY = DATA / "portfolio/capital_flow_policy.json"
FUNDING_PLAN = DATA / "capital/funding_plan.json"
FAMILY_BUNDLE = DATA / "capital/family_office_bundle.json"

EXPECTED_POOLS = {"crypto_exchange_pool", "ibkr_pool"}
EXPECTED_LT_SHARE = 0.37


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


context = read_json(CAPITAL_CONTEXT, {}) or {}
policy = read_json(CAPITAL_POLICY, {}) or {}
funding = read_json(FUNDING_PLAN, {}) or {}
family = read_json(FAMILY_BUNDLE, {}) or {}

transfers = funding.get("transfers") or []
guardrails = funding.get("guardrails") or {}
tax_cfg = policy.get("tax") or {}

funding_pools = sorted({
    t.get("target_pool")
    for t in transfers
    if isinstance(t, dict) and t.get("target_pool")
})

reserve_values = {
    "tax_reserve_pct": tax_cfg.get("rate"),
    "bfr_reserve_pct": 0.10,
    "security_reserve_pct": 0.03,
    "lt_share": EXPECTED_LT_SHARE,
}

failed = []

if context.get("environment") != "PREPROD" or context.get("real_money_enabled") is not False:
    failed.append({
        "check": "preprod_virtual_context",
        "severity": "critical",
        "detail": "Capital context must remain PREPROD / no real money.",
        "evidence": context,
    })

missing_pools = sorted(EXPECTED_POOLS - set(funding_pools))
if missing_pools:
    failed.append({
        "check": "funding_pools_present",
        "severity": "warning",
        "detail": "Expected funding pools missing from current transfer plan.",
        "evidence": {"missing": missing_pools, "found": funding_pools},
    })

if tax_cfg.get("enabled") is not True or float(tax_cfg.get("rate", 0)) < 0.25:
    failed.append({
        "check": "tax_reserve_policy",
        "severity": "critical",
        "detail": "Tax reserve must be enabled and at least 25%.",
        "evidence": tax_cfg,
    })

if guardrails.get("automatic_transfers_allowed") is not False:
    failed.append({
        "check": "automatic_transfers_disabled",
        "severity": "critical",
        "detail": "Automatic funding transfers must remain disabled.",
        "evidence": guardrails,
    })

if guardrails.get("inter_broker_transfer_auto_allowed") is not False:
    failed.append({
        "check": "inter_broker_auto_disabled",
        "severity": "critical",
        "detail": "Inter-broker transfers must remain manual.",
        "evidence": guardrails,
    })

if guardrails.get("requires_governance_approval") is not True:
    failed.append({
        "check": "governance_required",
        "severity": "critical",
        "detail": "Funding transfers must require governance approval.",
        "evidence": guardrails,
    })

bad_transfers = [
    t for t in transfers
    if isinstance(t, dict)
    and (
        t.get("manual_transfer_required") is not True
        or t.get("requires_governance_approval") is not True
        or t.get("status") != "manual_review_required"
    )
]

if bad_transfers:
    failed.append({
        "check": "all_transfers_manual_review",
        "severity": "critical",
        "detail": "All current funding transfers must require manual review and governance.",
        "evidence": bad_transfers,
    })

status = "ok"
if any(f["severity"] == "critical" for f in failed):
    status = "critical"
elif failed:
    status = "warning"

result = {
    "generated_at": utc_now(),
    "status": status,
    "master_intent": {
        "mission": "Protect NSC capital structure, treasury, reserves and funding governance.",
        "rules": [
            "manual_inter_universe_transfers",
            "no_automatic_funding",
            "tax_reserve_from_first_euro",
            "bfr_and_security_reserves",
            "lt_compounding",
            "funding_pool_separation"
        ],
        "preprod_mode": "virtual / simulated only"
    },
    "summary": {
        "capital_mode": context.get("capital_mode"),
        "real_money_enabled": context.get("real_money_enabled"),
        "funding_pools": funding_pools,
        "reserve_values": reserve_values,
        "guardrails": guardrails,
        "transfers_count": len(transfers),
        "manual_review_transfers": sum(1 for t in transfers if isinstance(t, dict) and t.get("status") == "manual_review_required"),
        "family_bundle_present": isinstance(family, dict) and bool(family),
    },
    "failed_checks": failed,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": status,
    "summary": result["summary"],
    "failed_checks": failed,
}, indent=2, ensure_ascii=False))
