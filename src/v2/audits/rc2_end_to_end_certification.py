from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")

OUTPUT = (
    PREPROD
    / "audits"
    / "rc2_end_to_end_certification.json"
)

AUDITS = {
    "crypto": (
        DATA
        / "audits"
        / "crypto_master_strategy_audit.json"
    ),
    "equities_offensive": (
        DATA
        / "audits"
        / "equities_offensive_master_strategy_audit.json"
    ),
    "equities_defensive": (
        DATA
        / "audits"
        / "equities_defensive_master_strategy_audit.json"
    ),
    "bonds": (
        DATA
        / "audits"
        / "bonds_master_strategy_audit.json"
    ),
    "precious_metals": (
        DATA
        / "audits"
        / "precious_metals_master_strategy_audit.json"
    ),
    "options_us": (
        DATA
        / "audits"
        / "options_us_master_strategy_audit.json"
    ),
    "long_term_global": (
        DATA
        / "audits"
        / "long_term_global_master_strategy_audit.json"
    ),
    "portfolio_engine": (
        PREPROD
        / "audits"
        / "portfolio_engine_master_audit.json"
    ),
    "capital_funding": (
        DATA
        / "audits"
        / "capital_funding_master_audit.json"
    ),
    "governance_risk": (
        DATA
        / "audits"
        / "governance_risk_master_audit.json"
    ),
    "executive_decision": (
        PREPROD
        / "portfolio"
        / "audit"
        / "executive_decision_master_audit.json"
    ),
    "master_to_bricks": (
        DATA
        / "audits"
        / "master_to_bricks_audit.json"
    ),
    "master_semantic": (
        DATA
        / "audits"
        / "master_semantic_audit.json"
    ),
}

PORTFOLIO_STATE = (
    PREPROD
    / "portfolio"
    / "state"
    / "portfolio_state.json"
)

PORTFOLIO_TARGET = (
    PREPROD
    / "portfolio"
    / "portfolio_target.json"
)

CAPITAL_STATE = (
    PREPROD
    / "portfolio"
    / "capital_state.json"
)

KILL_SWITCH = (
    PREPROD
    / "trading"
    / "kill_switch.json"
)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "missing",
            "_path": str(path),
        }

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        return {
            "status": "error",
            "_path": str(path),
            "_error": str(exc),
        }

    if not isinstance(value, dict):
        return {
            "status": "error",
            "_path": str(path),
            "_error": "json_root_not_object",
        }

    return value


def add_check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    ok: bool,
    severity: str = "critical",
    evidence: Any = None,
) -> None:
    checks.append(
        {
            "name": name,
            "ok": bool(ok),
            "severity": severity,
            "evidence": evidence,
        }
    )


def main() -> int:
    checks: list[dict[str, Any]] = []

    audit_docs = {
        name: read_json(path)
        for name, path in AUDITS.items()
    }

    for name, doc in audit_docs.items():
        add_check(
            checks,
            name=f"audit_{name}",
            ok=doc.get("status") == "ok",
            evidence={
                "status": doc.get("status"),
                "path": str(AUDITS[name]),
            },
        )

    state = read_json(PORTFOLIO_STATE)
    target = read_json(PORTFOLIO_TARGET)
    capital = read_json(CAPITAL_STATE)
    kill = read_json(KILL_SWITCH)

    expected_tactical = {
        "crypto",
        "equities_offensive",
        "equities_defensive",
        "bonds",
        "precious_metals",
        "options_us",
    }

    bricks = state.get("bricks") or {}
    target_weights = (
        target.get("final_brick_weights")
        or target.get("brick_weights")
        or {}
    )

    add_check(
        checks,
        name="portfolio_state_exact_tactical_identity",
        ok=set(bricks) == expected_tactical,
        evidence=sorted(bricks),
    )

    add_check(
        checks,
        name="portfolio_target_exact_tactical_identity",
        ok=set(target_weights) == expected_tactical,
        evidence=sorted(target_weights),
    )

    add_check(
        checks,
        name="legacy_options_identity_absent",
        ok=(
            "options_v2_shadow" not in bricks
            and "options_v3_shadow" not in bricks
            and "options_v2_shadow" not in target_weights
            and "options_v3_shadow" not in target_weights
        ),
        evidence={
            "state_keys": sorted(bricks),
            "target_keys": sorted(target_weights),
        },
    )

    tactical_sum = sum(
        float(target_weights.get(name) or 0.0)
        for name in expected_tactical
    )

    add_check(
        checks,
        name="tactical_target_sum_90pct",
        ok=abs(tactical_sum - 0.9) <= 0.000001,
        evidence=round(tactical_sum, 6),
    )

    add_check(
        checks,
        name="capital_total_26000",
        ok=capital.get("total_capital_eur") == 26000.0,
        evidence=capital.get("total_capital_eur"),
    )

    add_check(
        checks,
        name="capital_deployable_25000",
        ok=capital.get("deployable_capital_eur") == 25000.0,
        evidence=capital.get("deployable_capital_eur"),
    )

    add_check(
        checks,
        name="cash_reserve_1000",
        ok=capital.get("cash_reserve_eur") == 1000.0,
        evidence=capital.get("cash_reserve_eur"),
    )

    options = (
        bricks.get("options_us")
        if isinstance(bricks, dict)
        else None
    ) or {}

    risk_flags = options.get("risk_flags") or {}

    add_check(
        checks,
        name="options_us_governed_target",
        ok=options.get("governed_target") is True,
        evidence=options.get("governed_target"),
    )

    add_check(
        checks,
        name="options_us_active_role",
        ok=options.get("portfolio_role") == "active_options",
        evidence=options.get("portfolio_role"),
    )

    add_check(
        checks,
        name="options_us_ibkr_pool",
        ok=options.get("funding_pool") == "ibkr_pool",
        evidence=options.get("funding_pool"),
    )

    add_check(
        checks,
        name="options_simulation_mode",
        ok=risk_flags.get("simulation_mode") is True,
        evidence=risk_flags.get("simulation_mode"),
    )

    add_check(
        checks,
        name="options_execution_blocked",
        ok=risk_flags.get("execution_blocked") is True,
        evidence=risk_flags.get("execution_blocked"),
    )

    add_check(
        checks,
        name="options_real_money_disabled",
        ok=risk_flags.get("real_money_disabled") is True,
        evidence=risk_flags.get("real_money_disabled"),
    )

    add_check(
        checks,
        name="options_safety_contract_ok",
        ok=risk_flags.get("safety_contract_ok") is True,
        evidence=risk_flags.get("safety_contract_ok"),
    )

    add_check(
        checks,
        name="kill_switch_not_hard_blocked",
        ok=kill.get("hard_block") is not True,
        evidence=kill.get("hard_block"),
    )

    failed_checks = [
        row
        for row in checks
        if row.get("ok") is not True
    ]

    critical_failures = [
        row
        for row in failed_checks
        if row.get("severity") == "critical"
    ]

    warning_failures = [
        row
        for row in failed_checks
        if row.get("severity") == "warning"
    ]

    if critical_failures:
        status = "critical"
        decision = "BLOCKED"
    elif warning_failures:
        status = "warning"
        decision = "PASS_WITH_WARNINGS"
    else:
        status = "ok"
        decision = "PASS"

    result = {
        "status": status,
        "engine": "rc2_end_to_end_certification_v1",
        "generated_at": utc_now(),
        "environment": "PREPROD",
        "release_candidate": "RC2",
        "execution_policy": "SIMULATED_ONLY",
        "production_authorized": False,
        "real_execution_allowed": False,
        "decision": decision,
        "summary": {
            "audit_count": len(AUDITS),
            "checks_total": len(checks),
            "checks_passed": (
                len(checks) - len(failed_checks)
            ),
            "checks_failed": len(failed_checks),
            "critical_failures": len(critical_failures),
            "warning_failures": len(warning_failures),
        },
        "audit_statuses": {
            name: doc.get("status")
            for name, doc in audit_docs.items()
        },
        "checks": checks,
        "failed_checks": failed_checks,
        "critical_failures": critical_failures,
        "warning_failures": warning_failures,
        "contracts": {
            "options_identity": "options_us",
            "tactical_bricks": sorted(
                expected_tactical
            ),
            "total_capital_eur": 26000.0,
            "deployable_capital_eur": 25000.0,
            "cash_reserve_eur": 1000.0,
            "tactical_target_sum": 0.9,
        },
        "notes": [
            (
                "RC1 end-to-end certifier is historical "
                "and is not used by RC2."
            ),
            (
                "RC2 certification consumes current "
                "base master audits and canonical PREPROD state."
            ),
            (
                "RC2 certification is intentionally independent "
                "from the PREPROD Go/No-Go audit to prevent "
                "circular certification dependencies."
            ),
            (
                "PASS certifies continued PREPROD "
                "observation only; it does not authorize "
                "production or real-money execution."
            ),
        ],
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": status,
                "decision": decision,
                "summary": result["summary"],
                "failed_checks": [
                    row.get("name")
                    for row in failed_checks
                ],
                "output": str(OUTPUT),
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
