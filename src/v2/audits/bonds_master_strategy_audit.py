from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")
OUTPUT = DATA / "audits" / "bonds_master_strategy_audit.json"

PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "portfolio_input": ROOT / "src/v2/data/portfolio/inputs/bonds_portfolio_input.json",
    "bond_signal": ROOT / "data/bonds/bond_signal.json",
    "bond_state": PREPROD / "bonds/bond_state.json",
    "funding_plan": DATA / "capital/funding_plan.json",
    "family_office_bundle": DATA / "capital/family_office_bundle.json",
}

EXPECTED_ROLE = "macro_stabilizer"
EXPECTED_POOL = "ibkr_pool"
EXPECTED_ASSETS = {"SHY", "IEF", "TLT", "LQD"}


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
    portfolio_input = docs["portfolio_input"]
    bond_signal = docs["bond_signal"]
    bond_state = docs["bond_state"]
    funding_plan = docs["funding_plan"]
    family_office = docs["family_office_bundle"]

    allocation = portfolio_input.get("allocation", {}) if isinstance(portfolio_input, dict) else {}
    assets = set(str(k).upper() for k in allocation.keys())

    drivers = portfolio_input.get("drivers", {}) if isinstance(portfolio_input, dict) else {}
    risk_flags = portfolio_input.get("risk_flags", {}) if isinstance(portfolio_input, dict) else {}
    inertia = portfolio_input.get("inertia_profile", {}) if isinstance(portfolio_input, dict) else {}

    checks = [
        check(
            "preprod_virtual_mode",
            context.get("environment") == "PREPROD"
            and context.get("capital_mode") == "virtual"
            and context.get("real_money_enabled") is False,
            "critical",
            "Bonds must run in virtual PREPROD mode.",
            context,
        ),
        check(
            "portfolio_role_macro_stabilizer",
            portfolio_input.get("portfolio_role") == EXPECTED_ROLE,
            "critical",
            "Bonds must act as macro_stabilizer.",
            portfolio_input.get("portfolio_role"),
        ),
        check(
            "funding_pool_ibkr",
            portfolio_input.get("funding_pool") == EXPECTED_POOL,
            "critical",
            "Bonds must use IBKR funding pool.",
            portfolio_input.get("funding_pool"),
        ),
        check(
            "allocation_present",
            isinstance(allocation, dict) and len(allocation) > 0,
            "critical",
            "Bond allocation must exist.",
            allocation,
        ),
        check(
            "expected_bond_assets_present",
            len(assets & EXPECTED_ASSETS) >= 3,
            "warning",
            "Bond allocation should include short/intermediate/long/credit sleeves.",
            sorted(assets),
        ),
        check(
            "duration_target_present",
            bool(portfolio_input.get("duration_target")),
            "warning",
            "Bond duration target should be explicit.",
            portfolio_input.get("duration_target"),
        ),
        check(
            "drivers_present",
            isinstance(drivers, dict) and len(drivers) >= 4,
            "warning",
            "Bond macro drivers should be present.",
            drivers,
        ),
        check(
            "risk_flags_present",
            isinstance(risk_flags, dict) and len(risk_flags) > 0,
            "warning",
            "Bond risk flags should be present.",
            risk_flags,
        ),
        check(
            "inertia_low_or_medium",
            inertia.get("rebalance_frequency") in {"low", "medium"},
            "warning",
            "Bonds should rebalance slowly versus alpha bricks.",
            inertia,
        ),
        check(
            "signal_exists",
            isinstance(bond_signal, dict) and bool(bond_signal),
            "warning",
            "Bond signal artifact should exist.",
            bond_signal,
        ),
        check(
            "state_exists",
            isinstance(bond_state, dict) and bool(bond_state),
            "warning",
            "Bond preprod state should exist.",
            bond_state,
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
        "engine": "bonds_master_strategy_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "master_intent": {
            "mission": "Provide macro stabilization, rate sensitivity control, credit cushion and defensive ballast.",
            "portfolio_role": EXPECTED_ROLE,
            "funding_pool": EXPECTED_POOL,
            "preprod_mode": "virtual / simulated only",
        },
        "summary": {
            "portfolio_target_weight": portfolio_input.get("target_weight"),
            "portfolio_role": portfolio_input.get("portfolio_role"),
            "funding_pool": portfolio_input.get("funding_pool"),
            "regime": portfolio_input.get("regime"),
            "confidence": portfolio_input.get("confidence"),
            "duration_target": portfolio_input.get("duration_target"),
            "allocation": allocation,
            "assets": sorted(assets),
            "drivers": drivers,
            "risk_flags": risk_flags,
            "inertia_profile": inertia,
            "bond_state_status": bond_state.get("status") if isinstance(bond_state, dict) else None,
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
