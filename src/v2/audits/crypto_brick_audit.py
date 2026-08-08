from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")
OUTPUT = DATA / "audits" / "crypto_brick_audit.json"


PATHS = {
    "capital_allocation": PREPROD / "trading/capital_allocation.json",
    "capital_config": PREPROD / "trading/capital_config.json",
    "execution_plan": PREPROD / "trading/execution_plan.json",
    "execution_plan_simulated": PREPROD / "trading/execution_plan_simulated.json",
    "open_positions": PREPROD / "trading/open_positions.json",
    "sized_signals": PREPROD / "trading/sized_signals.json",
    "selected_tokens": PREPROD / "selected_tokens.json",
    "dynamic_tokens": PREPROD / "trading/selected_tokens.dynamic.json",
    "market_regime": PREPROD / "analysis/market_regime_detector.json",
    "governance": PREPROD / "analysis/governance_engine_pro.json",
    "kill_switch": PREPROD / "trading/kill_switch.json",
    "worst_trades": PREPROD / "risk/worst_trades.json",
    "portfolio_input": ROOT / "src/v2/data/portfolio/inputs/crypto_portfolio_input.json",
    "capital_context": DATA / "capital/config/capital_context.json",
}


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
        for key in ("items", "tokens", "signals", "orders", "positions", "trades"):
            if isinstance(x.get(key), list):
                return x.get(key)
    return []


def check(name: str, ok: bool, severity: str, detail: str) -> Dict[str, Any]:
    return {
        "check": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
    }


def status_from_checks(checks: List[Dict[str, Any]]) -> str:
    if any((not c["ok"]) and c["severity"] == "critical" for c in checks):
        return "critical"
    if any((not c["ok"]) and c["severity"] == "warning" for c in checks):
        return "warning"
    return "ok"


def contains_live_marker(payload: Any) -> bool:
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
    ]
    return any(d in raw for d in dangerous)


def main() -> None:
    docs = {k: read_json(p, {}) for k, p in PATHS.items()}

    capital_context = docs["capital_context"]
    execution_plan = docs["execution_plan"]
    execution_plan_simulated = docs["execution_plan_simulated"]
    selected_tokens = as_list(docs["selected_tokens"])
    dynamic_tokens = as_list(docs["dynamic_tokens"])
    sized_signals = as_list(docs["sized_signals"])
    open_positions = as_list(docs["open_positions"])
    portfolio_input = docs["portfolio_input"]
    governance = docs["governance"]
    kill_switch = docs["kill_switch"]
    market_regime = docs["market_regime"]

    action_policy = execution_plan.get("action_policy") if isinstance(execution_plan, dict) else None
    exec_orders = as_list(execution_plan.get("orders", [])) if isinstance(execution_plan, dict) else []
    candidate_orders = as_list(execution_plan.get("candidate_orders", [])) if isinstance(execution_plan, dict) else []

    checks = [
        check(
            "capital_is_virtual_preprod",
            capital_context.get("environment") == "PREPROD"
            and capital_context.get("capital_mode") == "virtual"
            and capital_context.get("real_money_enabled") is False,
            "critical",
            "Crypto must run on virtual PREPROD capital."
        ),
        check(
            "no_live_execution_marker",
            not contains_live_marker([execution_plan, execution_plan_simulated, governance, kill_switch]),
            "critical",
            "Crypto must not expose live execution markers."
        ),
        check(
            "action_policy_safe",
            str(action_policy).upper() in {"SIMULATED_EXECUTION", "SIMULATED_ONLY", "SIMULATED_AND_PAPER", "PAPER"},
            "critical",
            "Crypto execution action_policy must remain simulated/paper."
        ),
        check(
            "portfolio_input_exists",
            isinstance(portfolio_input, dict) and portfolio_input.get("brick") == "crypto",
            "critical",
            "Crypto must export standardized Portfolio Engine input."
        ),
        check(
            "portfolio_role_alpha",
            portfolio_input.get("portfolio_role") == "alpha_aggressive",
            "warning",
            "Crypto role should be alpha_aggressive."
        ),
        check(
            "funding_pool_crypto",
            portfolio_input.get("funding_pool") == "crypto_exchange_pool",
            "critical",
            "Crypto must use crypto_exchange_pool."
        ),
        check(
            "selected_tokens_present",
            len(selected_tokens) > 0 or len(dynamic_tokens) > 0,
            "warning",
            "Crypto should have selected/dynamic tokens available."
        ),
        check(
            "market_regime_present",
            isinstance(market_regime, dict) and bool(market_regime),
            "warning",
            "Crypto should consume market regime."
        ),
        check(
            "governance_present",
            isinstance(governance, dict) and bool(governance),
            "critical",
            "Crypto must consume governance."
        ),
        check(
            "kill_switch_present",
            isinstance(kill_switch, dict) and bool(kill_switch),
            "warning",
            "Crypto kill switch artifact should exist."
        ),
        check(
            "execution_plan_present",
            isinstance(execution_plan, dict) and bool(execution_plan),
            "critical",
            "Crypto execution plan must exist."
        ),
        check(
            "sized_signals_artifact_present",
            docs["sized_signals"] not in ({}, None),
            "warning",
            "Sized signals artifact should exist."
        ),
    ]

    report = {
        "status": status_from_checks(checks),
        "engine": "crypto_brick_audit_v1",
        "mode": "read_only",
        "timestamp": utc_now(),
        "summary": {
            "action_policy": action_policy,
            "candidate_orders": len(candidate_orders),
            "orders": len(exec_orders),
            "sized_signals": len(sized_signals),
            "open_positions": len(open_positions),
            "selected_tokens": len(selected_tokens),
            "dynamic_tokens": len(dynamic_tokens),
            "portfolio_target_weight": portfolio_input.get("target_weight"),
            "portfolio_role": portfolio_input.get("portfolio_role"),
            "funding_pool": portfolio_input.get("funding_pool"),
            "market_regime": market_regime.get("regime") or market_regime.get("market_regime"),
            "governance_flag": governance.get("flag") or governance.get("status"),
        },
        "checks": checks,
        "files": {k: str(v) for k, v in PATHS.items()},
    }

    report["failed_checks"] = [c for c in checks if not c["ok"]]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "summary": report["summary"],
        "failed_checks": report["failed_checks"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
