from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


CAPITAL_CONTEXT_PATH = Path("data/capital/config/capital_context.json")
ENTERPRISE_VALUE_PATH = Path("data/capital/enterprise_value.json")
COLLATERAL_STATE_PATH = Path("data/capital/collateral_state.json")
TREASURY_STATE_PATH = Path("data/capital/treasury_state.json")
PORTFOLIO_STATE_NORMALIZED_PATH = Path("data/capital/portfolio_state_normalized.json")
REBALANCE_PLAN_PATH = Path("data/capital/rebalance_plan.json")
FUNDING_PLAN_PATH = Path("data/capital/funding_plan.json")
CAPITAL_METRICS_PATH = Path("data/capital/capital_metrics.json")
SURVIVAL_STATE_PATH = Path("data/capital/survival_state.json")

OUTPUT_PATH = Path("data/capital/family_office_bundle.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run() -> Dict[str, Any]:
    capital_context = read_json(CAPITAL_CONTEXT_PATH, default={}) or {}
    enterprise_value = read_json(ENTERPRISE_VALUE_PATH, default={}) or {}
    collateral_state = read_json(COLLATERAL_STATE_PATH, default={}) or {}
    treasury_state = read_json(TREASURY_STATE_PATH, default={}) or {}
    portfolio_state = read_json(PORTFOLIO_STATE_NORMALIZED_PATH, default={}) or {}
    rebalance_plan = read_json(REBALANCE_PLAN_PATH, default={}) or {}
    funding_plan = read_json(FUNDING_PLAN_PATH, default={}) or {}
    capital_metrics = read_json(CAPITAL_METRICS_PATH, default={}) or {}
    survival_state = read_json(SURVIVAL_STATE_PATH, default={}) or {}

    enterprise = enterprise_value.get("enterprise_value", {}) if isinstance(enterprise_value, dict) else {}
    treasury = treasury_state.get("treasury", {}) if isinstance(treasury_state, dict) else {}
    collateral = collateral_state if isinstance(collateral_state, dict) else {}

    out = {
        "status": "ok",
        "engine": "family_office_bundle_engine_v1",
        "capital_context": capital_context,
        "headline": {
            "environment": capital_context.get("environment", "UNKNOWN"),
            "capital_mode": capital_context.get("capital_mode", "unknown"),
            "valuation_mode": capital_context.get("enterprise_valuation_mode", "unknown"),
            "enterprise_net_value_eur": enterprise.get("net_value_eur", 0.0),
            "nav_eur": enterprise.get("nav_eur", 0.0),
            "liquid_cash_eur": enterprise.get("liquid_cash_eur", 0.0),
            "treasury_health": (treasury_state.get("health") or {}).get("treasury_health", "unknown"),
            "collateral_status": collateral.get("ltv_status", "unknown"),
            "survival_mode": survival_state.get("mode", "UNKNOWN")
        },
        "enterprise_value": enterprise_value,
        "portfolio_state": portfolio_state,
        "treasury_state": treasury_state,
        "collateral_state": collateral_state,
        "rebalance_plan": rebalance_plan,
        "funding_plan": funding_plan,
        "capital_metrics": capital_metrics,
        "survival_state": survival_state,
        "ui_cards": {
            "enterprise_value": {
                "title": "Enterprise Value",
                "value": enterprise.get("net_value_eur", 0.0),
                "unit": "EUR",
                "mode": capital_context.get("enterprise_valuation_mode", "unknown")
            },
            "treasury": {
                "title": "Treasury",
                "cash_eur": treasury.get("liquid_cash_eur", 0.0),
                "total_treasury_eur": treasury.get("total_treasury_eur", 0.0),
                "health": (treasury_state.get("health") or {}).get("treasury_health", "unknown")
            },
            "collateral": {
                "title": "Collateral",
                "eligible_value_eur": collateral.get("eligible_collateral_value_eur", 0.0),
                "ltv_current": collateral.get("ltv_current", 0.0),
                "status": collateral.get("ltv_status", "unknown"),
                "new_debt_allowed": (collateral.get("governance") or {}).get("new_debt_allowed", False)
            },
            "funding": {
                "title": "Funding",
                "status": funding_plan.get("status", "unknown"),
                "manual_review_required": (funding_plan.get("kpis") or {}).get("manual_review_required", 0),
                "transfers_total": (funding_plan.get("kpis") or {}).get("transfers_total", 0)
            },
            "rebalance": {
                "title": "Rebalance",
                "status": rebalance_plan.get("status", "unknown"),
                "actions_proposed": (rebalance_plan.get("kpis") or {}).get("actions_proposed", 0)
            }
        },
        "warnings": [
            "PREPROD capital is virtual and simulated."
        ] if capital_context.get("capital_mode") == "virtual" else [],
        "updated_at": utc_now()
    }

    write_json(OUTPUT_PATH, out)
    return out


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
