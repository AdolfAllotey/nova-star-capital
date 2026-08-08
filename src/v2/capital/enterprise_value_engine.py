from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
CAPITAL_CONTEXT_PATH = Path("data/capital/config/capital_context.json")
PORTFOLIO_STATE_PATH = Path("data/capital/portfolio_state.json")
CAPITAL_METRICS_PATH = Path("data/capital/capital_metrics.json")
FUNDING_PLAN_PATH = Path("data/capital/funding_plan.json")
SURVIVAL_STATE_PATH = Path("data/capital/survival_state.json")

OUTPUT_PATH = Path("data/capital/enterprise_value.json")
AUDIT_PATH = Path("data/capital/audit/enterprise_value_events.jsonl")


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


def append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def pct(part: float, total: float) -> float:
    return round(part / total, 6) if total else 0.0


def run() -> Dict[str, Any]:
    capital = read_json(CAPITAL_STATE_PATH, default={}) or {}
    context = read_json(CAPITAL_CONTEXT_PATH, default={}) or {}
    portfolio = read_json(PORTFOLIO_STATE_PATH, default={}) or {}
    metrics = read_json(CAPITAL_METRICS_PATH, default={}) or {}
    funding = read_json(FUNDING_PLAN_PATH, default={}) or {}
    survival = read_json(SURVIVAL_STATE_PATH, default={}) or {}

    nav = safe_float(capital.get("total_nav_eur", portfolio.get("nav_eur", 0.0)))
    debt = safe_float(capital.get("borrowed_amount_eur", 0.0))
    collateral = safe_float(capital.get("collateral_value_eur", 0.0))
    liquid_cash = safe_float(capital.get("liquid_cash_eur", 0.0))

    reserves = {
        "tax_reserve_eur": safe_float(capital.get("tax_reserve_eur", 0.0)),
        "bfr_reserve_eur": safe_float(capital.get("bfr_reserve_eur", 0.0)),
        "security_reserve_eur": safe_float(capital.get("security_reserve_eur", 0.0))
    }

    trading_assets = {
        "crypto_trading_eur": safe_float(capital.get("crypto_trading_eur", 0.0)),
        "equities_offensive_eur": safe_float(capital.get("equities_offensive_eur", 0.0)),
        "options_eur": safe_float(capital.get("options_eur", 0.0))
    }

    long_term_assets = {
        "crypto_lt_eur": safe_float(capital.get("crypto_lt_eur", 0.0)),
        "equities_defensive_eur": safe_float(capital.get("equities_defensive_eur", 0.0)),
        "bonds_eur": safe_float(capital.get("bonds_eur", 0.0)),
        "gold_eur": safe_float(capital.get("gold_eur", 0.0))
    }

    portfolio_values = portfolio.get("current_values_eur", {}) if isinstance(portfolio.get("current_values_eur"), dict) else {}

    # If capital_state buckets are still empty, enrich valuation with portfolio_state known values.
    trading_total = sum(trading_assets.values())
    long_term_total = sum(long_term_assets.values())

    if trading_total == 0:
        trading_total = (
            safe_float(portfolio_values.get("crypto_trading", 0.0))
            + safe_float(portfolio_values.get("equities_offensive", 0.0))
        )

    if long_term_total == 0:
        long_term_total = (
            safe_float(portfolio_values.get("crypto_lt", 0.0))
            + safe_float(portfolio_values.get("equities_lt", 0.0))
            + safe_float(portfolio_values.get("bonds", 0.0))
            + safe_float(portfolio_values.get("gold", 0.0))
        )

    reserves_total = sum(reserves.values())
    enterprise_gross_value = nav + debt
    enterprise_net_value = nav - debt

    estimated_lombard_capacity_start = collateral * 0.25
    estimated_lombard_capacity_mature = collateral * 0.35
    remaining_lombard_capacity_start = max(0.0, estimated_lombard_capacity_start - debt)
    remaining_lombard_capacity_mature = max(0.0, estimated_lombard_capacity_mature - debt)

    out = {
        "status": "ok",
        "engine": "enterprise_value_engine_v1",
        "currency": "EUR",
        "capital_context": context,
        "enterprise_value": {
            "gross_value_eur": round(enterprise_gross_value, 2),
            "net_value_eur": round(enterprise_net_value, 2),
            "nav_eur": round(nav, 2),
            "debt_eur": round(debt, 2),
            "liquid_cash_eur": round(liquid_cash, 2)
        },
        "asset_blocks": {
            "trading_assets_eur": round(trading_total, 2),
            "long_term_assets_eur": round(long_term_total, 2),
            "reserves_eur": round(reserves_total, 2),
            "cash_eur": round(liquid_cash, 2),
            "collateral_value_eur": round(collateral, 2)
        },
        "asset_block_weights": {
            "trading_assets": pct(trading_total, nav),
            "long_term_assets": pct(long_term_total, nav),
            "reserves": pct(reserves_total, nav),
            "cash": pct(liquid_cash, nav),
            "debt_to_nav": pct(debt, nav),
            "collateral_to_nav": pct(collateral, nav)
        },
        "reserves": {k: round(v, 2) for k, v in reserves.items()},
        "trading_assets": {k: round(v, 2) for k, v in trading_assets.items()},
        "long_term_assets": {k: round(v, 2) for k, v in long_term_assets.items()},
        "collateral": {
            "eligible_value_eur": round(collateral, 2),
            "ltv_current": pct(debt, collateral),
            "estimated_capacity_start_ltv_25_eur": round(estimated_lombard_capacity_start, 2),
            "estimated_capacity_mature_ltv_35_eur": round(estimated_lombard_capacity_mature, 2),
            "remaining_capacity_start_eur": round(remaining_lombard_capacity_start, 2),
            "remaining_capacity_mature_eur": round(remaining_lombard_capacity_mature, 2),
            "crypto_collateral_allowed": False
        },
        "governance": {
            "survival_mode": survival.get("mode", "UNKNOWN"),
            "survival_hard_block": survival.get("hard_block", False),
            "funding_status": funding.get("status", "unknown"),
            "automatic_transfers_allowed": False
        },
        "ui": {
            "primary_headline": "NSC Enterprise Value",
            "primary_metric": round(enterprise_net_value, 2),
            "secondary_metrics": {
                "nav_eur": round(nav, 2),
                "cash_eur": round(liquid_cash, 2),
                "collateral_eur": round(collateral, 2),
                "debt_eur": round(debt, 2)
            }
        },
        "sources": {
            "capital_state": str(CAPITAL_STATE_PATH),
            "portfolio_state": str(PORTFOLIO_STATE_PATH),
            "capital_metrics": str(CAPITAL_METRICS_PATH),
            "funding_plan": str(FUNDING_PLAN_PATH),
            "survival_state": str(SURVIVAL_STATE_PATH)
        },
        "notes": [
            "Enterprise value is patrimonial and internal.",
            "This is not accounting valuation, not tax valuation, and not a regulated NAV.",
            "In PREPROD, enterprise value is simulated and based on virtual seed capital.",
            "V1 uses available capital/portfolio artifacts; broker reconciliation will improve accuracy later."
        ],
        "updated_at": utc_now()
    }

    write_json(OUTPUT_PATH, out)
    append_jsonl(AUDIT_PATH, {
        "ts": utc_now(),
        "event": "enterprise_value_updated",
        "net_value_eur": out["enterprise_value"]["net_value_eur"],
        "nav_eur": out["enterprise_value"]["nav_eur"],
        "collateral_value_eur": out["asset_blocks"]["collateral_value_eur"]
    })

    return out


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
