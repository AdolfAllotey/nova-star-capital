from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")
OUTPUT = DATA / "audits" / "equities_offensive_master_strategy_audit.json"

PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "portfolio_input": ROOT / "src/v2/data/portfolio/inputs/equities_offensive_portfolio_input.json",
    "dashboard_payload": ROOT / "data/equities_offensive/reporting/dashboard_payload.json",
    "ui_bundle": PREPROD / "equities_offensive/ui/ui_bundle.json",
    "state": PREPROD / "equities_offensive/state/state.json",
    "signals": PREPROD / "equities_offensive/signals/signals_v1.json",
    "execution_plan": PREPROD / "equities_offensive/execution/execution_plan.json",
    "market_regime": ROOT / "data/equities_offensive/market/market_regime.json",
    "long_term_policy": ROOT / "src/v2/config/offensive_lt_policy.json",
    "lt_positions": ROOT / "data/portfolio/long_term_positions.json",
    "capital_flow_policy": DATA / "portfolio/capital_flow_policy.json",
    "funding_plan": DATA / "capital/funding_plan.json",
}

EXPECTED_ROLE = "alpha_directional"
EXPECTED_POOL = "ibkr_pool"
EXPECTED_CORE_ASSETS = {"AMD", "NVDA", "META", "NFLX", "AVGO"}


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
        for key in ("signals", "orders", "positions", "items", "data", "candidates"):
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
    ]
    return any(d in raw for d in dangerous)


def get_symbol(row: Dict[str, Any]) -> str:
    return str(row.get("symbol") or row.get("ticker") or row.get("asset") or "").upper().strip()


def main() -> None:
    docs = {k: read_json(p, {}) for k, p in PATHS.items()}

    context = docs["capital_context"]
    portfolio_input = docs["portfolio_input"]
    dashboard = docs["dashboard_payload"]
    state = docs["state"]
    signals = as_list(docs["signals"])
    execution_plan = docs["execution_plan"]
    market_regime = docs["market_regime"]
    lt_policy = docs["long_term_policy"]
    lt_positions = docs["lt_positions"]
    funding_plan = docs["funding_plan"]

    orders = as_list(execution_plan.get("orders", [])) if isinstance(execution_plan, dict) else []
    candidate_orders = as_list(execution_plan.get("candidate_orders", [])) if isinstance(execution_plan, dict) else []

    allocation = portfolio_input.get("allocation", {}) if isinstance(portfolio_input, dict) else {}
    allocated_assets = set(str(k).upper() for k in allocation.keys())

    signal_symbols = [get_symbol(s) for s in signals if isinstance(s, dict) and get_symbol(s)]
    order_symbols = [get_symbol(o) for o in orders if isinstance(o, dict) and get_symbol(o)]

    lt_symbols = []
    if isinstance(lt_positions, dict):
        positions = lt_positions.get("positions", [])
        if isinstance(positions, list):
            lt_symbols = [get_symbol(p) for p in positions if isinstance(p, dict) and get_symbol(p)]

    checks = [
        check(
            "preprod_virtual_no_real_money",
            context.get("environment") == "PREPROD"
            and context.get("capital_mode") == "virtual"
            and context.get("real_money_enabled") is False,
            "critical",
            "Actions offensives must run on virtual PREPROD capital.",
            context,
        ),
        check(
            "no_live_execution",
            not contains_real_live_marker([execution_plan, state, dashboard]),
            "critical",
            "Actions offensives must not expose live execution markers.",
            {
                "action_policy": execution_plan.get("action_policy") if isinstance(execution_plan, dict) else None,
                "mode": execution_plan.get("mode") if isinstance(execution_plan, dict) else None,
            },
        ),
        check(
            "portfolio_role_alpha_directional",
            portfolio_input.get("portfolio_role") == EXPECTED_ROLE,
            "critical",
            "Actions offensives must be alpha_directional.",
            portfolio_input.get("portfolio_role"),
        ),
        check(
            "funding_pool_ibkr",
            portfolio_input.get("funding_pool") == EXPECTED_POOL,
            "critical",
            "Actions offensives must use IBKR pool.",
            portfolio_input.get("funding_pool"),
        ),
        check(
            "risk_on_regime_visible",
            portfolio_input.get("regime") in {"risk_on", "balanced", "risk_off"}
            or market_regime.get("regime") in {"risk_on", "balanced", "risk_off"},
            "warning",
            "Market regime should be visible and consumed.",
            {
                "portfolio_regime": portfolio_input.get("regime"),
                "market_regime": market_regime.get("regime") if isinstance(market_regime, dict) else None,
            },
        ),
        check(
            "allocation_not_empty",
            isinstance(allocation, dict) and len(allocation) > 0,
            "critical",
            "Portfolio allocation should not be empty.",
            allocation,
        ),
        check(
            "core_growth_assets_present",
            len(allocated_assets & EXPECTED_CORE_ASSETS) >= 3,
            "warning",
            "Allocation should include core offensive growth assets.",
            sorted(allocated_assets),
        ),
        check(
            "signals_present",
            len(signals) > 0 or int((portfolio_input.get("drivers") or {}).get("signals_count", 0) or 0) > 0,
            "warning",
            "Signals should exist or be summarized in drivers.",
            {
                "signals_file_count": len(signals),
                "drivers": portfolio_input.get("drivers"),
            },
        ),
        check(
            "execution_plan_present",
            isinstance(execution_plan, dict) and bool(execution_plan),
            "critical",
            "Execution plan should exist, even if simulated/empty.",
            None,
        ),
        check(
            "execution_candidates_or_risk_decisions_visible",
            len(candidate_orders) > 0
            or int((portfolio_input.get("drivers") or {}).get("risk_decisions_count", 0) or 0) > 0,
            "warning",
            "Risk decisions or candidate orders should be visible.",
            {
                "candidate_orders": len(candidate_orders),
                "drivers": portfolio_input.get("drivers"),
            },
        ),
        check(
            "lt_policy_exists",
            isinstance(lt_policy, dict) and bool(lt_policy.get("regimes")),
            "warning",
            "Offensive LT policy should exist for compounding.",
            lt_policy,
        ),
        check(
            "lt_positions_exist_or_policy_ready",
            len(lt_symbols) > 0 or isinstance(lt_policy, dict),
            "warning",
            "LT compounding should have positions or policy ready.",
            lt_symbols,
        ),
        check(
            "funding_manual_if_any",
            (funding_plan.get("guardrails") or {}).get("automatic_transfers_allowed") is False,
            "critical",
            "Funding into IBKR must remain manual/governed in PREPROD.",
            funding_plan.get("guardrails") if isinstance(funding_plan, dict) else None,
        ),
    ]

    report = {
        "status": status_from_checks(checks),
        "engine": "equities_offensive_master_strategy_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "master_intent": {
            "mission": "Generate directional equity alpha through offensive growth/quality/momentum signals, then support LT compounding.",
            "trading_bucket": "equities_offensive",
            "funding_pool": "ibkr_pool",
            "expected_role": EXPECTED_ROLE,
            "preprod_mode": "virtual / simulated only",
        },
        "summary": {
            "portfolio_target_weight": portfolio_input.get("target_weight"),
            "portfolio_role": portfolio_input.get("portfolio_role"),
            "funding_pool": portfolio_input.get("funding_pool"),
            "regime": portfolio_input.get("regime"),
            "confidence": portfolio_input.get("confidence"),
            "allocation": allocation,
            "allocated_assets": sorted(allocated_assets),
            "signals_count_file": len(signals),
            "signal_symbols": dict(Counter(signal_symbols)),
            "orders_count": len(orders),
            "candidate_orders_count": len(candidate_orders),
            "order_symbols": dict(Counter(order_symbols)),
            "drivers": portfolio_input.get("drivers"),
            "lt_symbols_count": len(lt_symbols),
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
