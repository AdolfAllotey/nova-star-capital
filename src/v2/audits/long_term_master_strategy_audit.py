from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
OUTPUT = DATA / "audits" / "long_term_master_strategy_audit.json"

PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "lt_portfolio": DATA / "portfolio/lt_portfolio.json",
    "long_term_positions": DATA / "portfolio/long_term_positions.json",
    "capital_flow_policy": DATA / "portfolio/capital_flow_policy.json",
    "funding_plan": DATA / "capital/funding_plan.json",
    "family_office_bundle": DATA / "capital/family_office_bundle.json",
}

# Current Master decision:
# Crypto LT is intentionally restricted to BTC / ETH / SOL.
EXPECTED_CRYPTO_LT = {
    "BTC": 0.50,
    "ETH": 0.30,
    "SOL": 0.20,
}

EXPECTED_LT_SHARE = 0.37


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"__error__": str(exc), "__path__": str(path)}


def as_list(x: Any) -> List[Any]:
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for key in ("positions", "holdings", "assets", "items", "data"):
            if isinstance(x.get(key), list):
                return x.get(key)
    return []


def check(name: str, ok: bool, severity: str, detail: str, evidence: Any = None) -> Dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    }


def status_from_checks(checks: List[Dict[str, Any]]) -> str:
    if any((not c["ok"]) and c["severity"] == "critical" for c in checks):
        return "critical"
    if any((not c["ok"]) and c["severity"] == "warning" for c in checks):
        return "warning"
    return "ok"


def main() -> None:
    docs = {k: read_json(v, {}) for k, v in PATHS.items()}

    context = docs["capital_context"]
    lt_portfolio = docs["lt_portfolio"]
    lt_positions = as_list(docs["long_term_positions"])
    capital_flow = docs["capital_flow_policy"]
    funding_plan = docs["funding_plan"]
    family_office = docs["family_office_bundle"]

    allocations = {}
    if isinstance(lt_portfolio, dict):
        allocations = (
            lt_portfolio.get("allocation")
            or lt_portfolio.get("target_allocation")
            or {}
        )

        # Real current schema:
        # data/portfolio/lt_portfolio.json stores crypto LT under positions.{symbol}.weight
        if not allocations and isinstance(lt_portfolio.get("positions"), dict):
            allocations = {
                symbol: payload.get("weight")
                for symbol, payload in lt_portfolio.get("positions", {}).items()
                if isinstance(payload, dict) and payload.get("weight") is not None
            }

        # Real current schema:
        # data/portfolio/lt_portfolio.json stores crypto LT under positions.{symbol}.weight
        if not allocations and isinstance(lt_portfolio.get("positions"), dict):
            allocations = {
                symbol: payload.get("weight")
                for symbol, payload in lt_portfolio.get("positions", {}).items()
                if isinstance(payload, dict) and payload.get("weight") is not None
            }

    allocation_sum = round(sum(float(v) for v in allocations.values()), 6) if allocations else 0

    checks = [
        check(
            "preprod_virtual_mode",
            context.get("environment") == "PREPROD"
            and context.get("real_money_enabled") is False,
            "critical",
            "Long-term allocation must remain PREPROD simulated.",
            context,
        ),
        check(
            "lt_allocation_exists",
            isinstance(allocations, dict) and len(allocations) > 0,
            "critical",
            "Long-term allocation must exist.",
            {"allocation_count": len(allocations)},
        ),
        check(
            "lt_allocation_sum_valid",
            abs(allocation_sum - 1.0) <= 0.01,
            "warning",
            "Long-term allocation should sum near 100%.",
            {"sum": allocation_sum},
        ),
        check(
            "crypto_lt_matches_master",
            set(EXPECTED_CRYPTO_LT.keys()).issubset(set(allocations.keys())),
            "critical",
            "Crypto LT allocation must contain official NSC LT assets.",
            {"found_assets": sorted(list(allocations.keys()))},
        ),
        check(
            "lt_share_policy_respected",
            abs(float(
                capital_flow.get("long_term_bucket_share", EXPECTED_LT_SHARE)
            ) - EXPECTED_LT_SHARE) <= 0.001,
            "warning",
            "Long-term bucket share should remain 37% per NSC policy.",
            capital_flow.get("long_term_bucket_share"),
        ),
        check(
            "manual_funding_only",
            (funding_plan.get("guardrails") or {}).get("automatic_transfers_allowed") is False,
            "critical",
            "Funding flows must remain governed/manual.",
            funding_plan.get("guardrails"),
        ),
        check(
            "family_office_connected",
            isinstance(family_office, dict) and family_office.get("status") == "ok",
            "warning",
            "Family Office layer should be connected.",
            family_office.get("headline") if isinstance(family_office, dict) else None,
        ),
    ]

    expected_vs_actual = {}

    for symbol, expected_weight in EXPECTED_CRYPTO_LT.items():
        actual = allocations.get(symbol)
        expected_vs_actual[symbol] = {
            "expected": expected_weight,
            "actual": actual,
        }

    report = {
        "status": status_from_checks(checks),
        "engine": "long_term_master_strategy_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "master_intent": {
            "mission": "Compound profits into resilient long-term strategic holdings.",
            "official_crypto_lt_allocation": EXPECTED_CRYPTO_LT,
            "official_lt_share": EXPECTED_LT_SHARE,
            "preprod_mode": "virtual / simulated only",
        },
        "summary": {
            "allocation_count": len(allocations),
            "allocation_sum": allocation_sum,
            "lt_positions_count": len(lt_positions),
            "allocations": allocations,
            "expected_vs_actual": expected_vs_actual,
        },
        "checks": checks,
        "failed_checks": [c for c in checks if not c["ok"]],
        "files": {k: str(v) for k, v in PATHS.items()},
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "summary": report["summary"],
        "failed_checks": report["failed_checks"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
