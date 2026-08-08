from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")
OUTPUT = DATA / "audits" / "master_semantic_audit.json"


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


def check(name: str, ok: bool, severity: str, detail: str) -> Dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
    }



def has_real_live_marker(payload: Any) -> bool:
    """
    Detect real live execution markers while ignoring harmless words like missing_live_price.
    """
    raw = json.dumps(payload).lower()
    false_positives = [
        "missing_live_price",
        "live_price",
        "live price",
    ]
    for fp in false_positives:
        raw = raw.replace(fp, "")

    dangerous = [
        '"execution_mode": "live"',
        '"action_policy": "live"',
        '"mode": "live"',
        '"real_money_enabled": true',
        '"real_broker_funding_enabled": true',
        '"live_trading": true',
        '"paper_trading": false',
        '"simulated": false',
    ]
    return any(d in raw for d in dangerous)


def status_from_checks(checks: List[Dict[str, Any]]) -> str:
    if any((not c["ok"]) and c["severity"] == "critical" for c in checks):
        return "critical"
    if any((not c["ok"]) and c["severity"] == "warning" for c in checks):
        return "warning"
    return "ok"


def audit_capital_funding() -> Dict[str, Any]:
    context = read_json(DATA / "capital/config/capital_context.json", {})
    funding = read_json(DATA / "capital/funding_plan.json", {})
    collateral = read_json(DATA / "capital/collateral_state.json", {})
    treasury = read_json(DATA / "capital/treasury_state.json", {})

    checks = [
        check(
            "capital_mode_virtual_preprod",
            context.get("environment") == "PREPROD" and context.get("capital_mode") == "virtual",
            "critical",
            "Capital must be clearly marked PREPROD/virtual before global preprod."
        ),
        check(
            "real_money_disabled",
            context.get("real_money_enabled") is False,
            "critical",
            "Real money must remain disabled in preprod."
        ),
        check(
            "broker_funding_disabled",
            context.get("real_broker_funding_enabled") is False,
            "critical",
            "Real broker funding must remain disabled."
        ),
        check(
            "debt_disabled",
            context.get("real_debt_enabled") is False and (collateral.get("governance") or {}).get("new_debt_allowed") is False,
            "critical",
            "Real debt / Lombard must be disabled in PREPROD."
        ),
        check(
            "funding_manual_review",
            (funding.get("guardrails") or {}).get("automatic_transfers_allowed") is False,
            "critical",
            "Funding transfers must not be automatic."
        ),
        check(
            "treasury_exists",
            treasury.get("status") == "ok",
            "warning",
            "Treasury state should be generated."
        ),
    ]

    return {"status": status_from_checks(checks), "checks": checks}


def audit_portfolio() -> Dict[str, Any]:
    target = read_json(PREPROD / "portfolio/portfolio_target.json", {})
    normalized = read_json(DATA / "capital/portfolio_state_normalized.json", {})
    rebalance = read_json(DATA / "capital/rebalance_plan.json", {})

    final_weights = target.get("final_brick_weights", {}) if isinstance(target, dict) else {}

    checks = [
        check(
            "portfolio_target_exists",
            target.get("status") == "ok",
            "critical",
            "Portfolio target must exist and be ok."
        ),
        check(
            "normalized_state_exists",
            normalized.get("status") == "ok",
            "critical",
            "Normalized portfolio state must exist."
        ),
        check(
            "rebalance_v3",
            rebalance.get("engine") == "rebalance_engine_v3",
            "warning",
            "Rebalance engine should be v3 to protect cash/LT pockets."
        ),
        check(
            "cash_not_reduced",
            not any(a.get("bucket") == "cash" and a.get("status") == "proposed" for a in rebalance.get("actions", [])),
            "critical",
            "Cash must not be proposed as a normal reduction bucket."
        ),
        check(
            "lt_not_reduced",
            not any(a.get("bucket") in {"crypto_lt", "equities_lt"} and a.get("status") == "proposed" for a in rebalance.get("actions", [])),
            "critical",
            "LT pockets must not be reduced outside survival."
        ),
        check(
            "offensive_weights_present",
            final_weights.get("crypto", 0) > 0 and final_weights.get("equities_offensive", 0) > 0,
            "warning",
            "In current aggressive/preprod phase, crypto and offensive equities should be active."
        ),
    ]

    return {"status": status_from_checks(checks), "checks": checks}


def audit_options() -> Dict[str, Any]:
    dashboard = read_json(PREPROD / "options_v3/options_v3_dashboard.json", {})
    positions = read_json(PREPROD / "options_v3/options_v3_positions.json", {})
    checks = [
        check(
            "options_dashboard_exists",
            isinstance(dashboard, dict) and bool(dashboard),
            "warning",
            "Options V3 dashboard should exist."
        ),
        check(
            "options_shadow_not_live",
            not has_real_live_marker(dashboard),
            "critical",
            "Options must not run in live mode during PREPROD."
        ),
        check(
            "options_positions_exist",
            bool(positions),
            "warning",
            "Options positions artifact should exist."
        ),
    ]
    return {"status": status_from_checks(checks), "checks": checks}


def audit_crypto() -> Dict[str, Any]:
    cap = read_json(PREPROD / "trading/capital_allocation.json", {})
    exec_plan = read_json(PREPROD / "trading/execution_plan.json", {})
    checks = [
        check(
            "crypto_capital_exists",
            isinstance(cap, dict) and bool(cap),
            "warning",
            "Crypto capital allocation should exist."
        ),
        check(
            "crypto_no_live_execution_marker",
            not has_real_live_marker(exec_plan),
            "critical",
            "Crypto execution plan must not indicate LIVE execution."
        ),
        check(
            "crypto_execution_plan_exists",
            bool(exec_plan),
            "warning",
            "Crypto execution plan should exist."
        ),
    ]
    return {"status": status_from_checks(checks), "checks": checks}


def audit_equities_offensive() -> Dict[str, Any]:
    state = read_json(PREPROD / "equities_offensive/state/state.json", {})
    exec_plan = read_json(PREPROD / "equities_offensive/execution/execution_plan.json", {})
    checks = [
        check(
            "offensive_state_exists",
            isinstance(state, dict) and bool(state),
            "warning",
            "Offensive equities state should exist."
        ),
        check(
            "offensive_not_live",
            not has_real_live_marker(exec_plan),
            "critical",
            "Offensive equities execution must not be live."
        ),
        check(
            "offensive_execution_exists",
            bool(exec_plan),
            "warning",
            "Offensive equities execution plan should exist."
        ),
    ]
    return {"status": status_from_checks(checks), "checks": checks}


def audit_defensive_bonds_metals() -> Dict[str, Any]:
    defensive = read_json(PREPROD / "defensive/defensive_state.json", {})
    bonds = read_json(PREPROD / "bonds/bond_state.json", {})
    metals = read_json(PREPROD / "metals/metals_state.json", {})

    checks = [
        check("defensive_state_exists", bool(defensive), "warning", "Defensive state should exist."),
        check("bonds_state_exists", bool(bonds), "warning", "Bonds state should exist."),
        check("metals_state_exists", bool(metals), "warning", "Metals state should exist."),
        check(
            "defensive_assets_not_live_execution",
            not has_real_live_marker([defensive, bonds, metals]),
            "critical",
            "Defensive/Bonds/Metals must not indicate LIVE execution."
        ),
    ]

    return {"status": status_from_checks(checks), "checks": checks}


def audit_api_ui() -> Dict[str, Any]:
    bundle = read_json(DATA / "capital/family_office_bundle.json", {})
    checks = [
        check(
            "family_office_bundle_exists",
            bundle.get("status") == "ok",
            "warning",
            "Family Office bundle should exist."
        ),
        check(
            "family_office_virtual_warning",
            "virtual" in json.dumps(bundle).lower() and "simulated" in json.dumps(bundle).lower(),
            "critical",
            "Family Office UI/API must expose virtual/simulated PREPROD context."
        ),
    ]
    return {"status": status_from_checks(checks), "checks": checks}


def run() -> Dict[str, Any]:
    audits = {
        "capital_funding": audit_capital_funding(),
        "portfolio": audit_portfolio(),
        "crypto": audit_crypto(),
        "equities_offensive": audit_equities_offensive(),
        "defensive_bonds_metals": audit_defensive_bonds_metals(),
        "options_us": audit_options(),
        "api_ui": audit_api_ui(),
    }

    report = {
        "status": "ok",
        "engine": "master_semantic_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "audits": audits,
    }

    report["summary"] = {
        "areas_total": len(audits),
        "areas_ok": sum(1 for a in audits.values() if a["status"] == "ok"),
        "areas_warning": sum(1 for a in audits.values() if a["status"] == "warning"),
        "areas_critical": sum(1 for a in audits.values() if a["status"] == "critical"),
        "checks_total": sum(len(a["checks"]) for a in audits.values()),
        "checks_failed": sum(1 for a in audits.values() for c in a["checks"] if not c["ok"]),
    }

    if report["summary"]["areas_critical"] > 0:
        report["status"] = "critical"
    elif report["summary"]["areas_warning"] > 0:
        report["status"] = "warning"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    run()
