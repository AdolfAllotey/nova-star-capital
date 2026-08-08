from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")
OUTPUT = DATA / "audits" / "options_us_master_strategy_audit.json"

PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "portfolio_input": PREPROD / "portfolio/inputs/options_us_portfolio_input.json",
    "dashboard": PREPROD / "options_v3/options_v3_dashboard.json",
    "positions": PREPROD / "options_v3/options_v3_positions.json",
    "portfolio": PREPROD / "options_v3/options_v3_portfolio.json",
    "status": PREPROD / "options_v3/options_v3_status.json",
    "trades": PREPROD / "options_v3/options_v3_trades.json",
    "funding_plan": DATA / "capital/funding_plan.json",
    "family_office_bundle": DATA / "capital/family_office_bundle.json",
}

EXPECTED_POOL = "ibkr_pool"


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
        for key in ("positions", "trades", "orders", "signals", "items", "data"):
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


def contains_real_live_marker(payload: Any) -> bool:
    raw = json.dumps(payload).lower()
    for fp in ["missing_live_price", "live_price", "live price"]:
        raw = raw.replace(fp, "")
    dangerous = [
        '"execution_mode": "live"',
        '"action_policy": "live"',
        '"mode": "live"',
        '"real_money_enabled": true',
        '"real_broker_funding_enabled": true',
        '"live_trading": true',
        '"broker_orders_allowed": true',
        '"real_execution_enabled": true',
    ]
    return any(d in raw for d in dangerous)


def main() -> None:
    docs = {k: read_json(v, {}) for k, v in PATHS.items()}

    context = docs["capital_context"]
    portfolio_input = docs["portfolio_input"]
    dashboard = docs["dashboard"]
    positions = as_list(docs["positions"])
    trades = as_list(docs["trades"])
    options_portfolio = docs["portfolio"]
    status_doc = docs["status"]
    funding_plan = docs["funding_plan"]
    family_office = docs["family_office_bundle"]

    role = portfolio_input.get("portfolio_role") if isinstance(portfolio_input, dict) else None
    funding_pool = portfolio_input.get("funding_pool") if isinstance(portfolio_input, dict) else None

    all_payload = [portfolio_input, dashboard, positions, trades, options_portfolio, status_doc]

    checks = [
        check(
            "preprod_virtual_mode",
            context.get("environment") == "PREPROD"
            and context.get("capital_mode") == "virtual"
            and context.get("real_money_enabled") is False,
            "critical",
            "Options US must run in virtual PREPROD mode.",
            context,
        ),
        check(
            "no_live_execution",
            not contains_real_live_marker(all_payload),
            "critical",
            "Options US must not expose live execution markers.",
            None,
        ),
        check(
            "not_core_alpha_brick",
            role not in {"alpha_aggressive", "alpha_directional"},
            "warning",
            "Options should remain overlay/satellite, not core alpha engine.",
            role,
        ),
        check(
            "funding_pool_ibkr_if_present",
            funding_pool in {EXPECTED_POOL, None, ""},
            "critical",
            "Options US must use IBKR pool if a funding pool is declared.",
            funding_pool,
        ),
        check(
            "dashboard_exists",
            isinstance(dashboard, dict) and bool(dashboard),
            "warning",
            "Options dashboard artifact should exist.",
            dashboard,
        ),
        check(
            "portfolio_exists",
            isinstance(options_portfolio, dict) and bool(options_portfolio),
            "warning",
            "Options portfolio artifact should exist.",
            options_portfolio,
        ),
        check(
            "positions_artifact_exists",
            docs["positions"] not in ({}, None),
            "warning",
            "Options positions artifact should exist, even if empty.",
            {"positions_count": len(positions)},
        ),
        check(
            "status_artifact_exists",
            isinstance(status_doc, dict) and bool(status_doc),
            "warning",
            "Options status artifact should exist.",
            status_doc,
        ),
        check(
            "manual_funding_only",
            (funding_plan.get("guardrails") or {}).get("automatic_transfers_allowed") is False,
            "critical",
            "Funding into IBKR must remain governed/manual.",
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

    report = {
        "status": status_from_checks(checks),
        "engine": "options_us_master_strategy_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "master_intent": {
            "mission": "Provide optional US options overlay for volatility, directional enhancement and hedging, without becoming core alpha in PREPROD.",
            "funding_pool": EXPECTED_POOL,
            "preprod_mode": "virtual / simulated/shadow only",
        },
        "summary": {
            "portfolio_target_weight": portfolio_input.get("target_weight") if isinstance(portfolio_input, dict) else None,
            "portfolio_role": role,
            "funding_pool": funding_pool,
            "dashboard_status": dashboard.get("status") if isinstance(dashboard, dict) else None,
            "status": status_doc.get("status") if isinstance(status_doc, dict) else None,
            "positions_count": len(positions),
            "trades_count": len(trades),
            "portfolio_keys": list(options_portfolio.keys()) if isinstance(options_portfolio, dict) else [],
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
