from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
CAPITAL_CONTEXT_PATH = Path("data/capital/config/capital_context.json")
FUNDING_PLAN_PATH = Path("data/capital/funding_plan.json")
OUTPUT_PATH = Path("data/capital/treasury_state.json")
AUDIT_PATH = Path("data/capital/audit/treasury_events.jsonl")


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


def classify_treasury_health(cash_weight: float, protected_reserve_weight: float) -> str:
    if cash_weight >= 0.10 and protected_reserve_weight >= 0.05:
        return "strong"
    if cash_weight >= 0.05:
        return "normal"
    if cash_weight >= 0.02:
        return "thin"
    return "weak"


def run() -> Dict[str, Any]:
    capital = read_json(CAPITAL_STATE_PATH, default={}) or {}
    context = read_json(CAPITAL_CONTEXT_PATH, default={}) or {}
    funding = read_json(FUNDING_PLAN_PATH, default={}) or {}

    nav = safe_float(capital.get("total_nav_eur", 0.0))
    cash = safe_float(capital.get("liquid_cash_eur", 0.0))
    tax = safe_float(capital.get("tax_reserve_eur", 0.0))
    bfr = safe_float(capital.get("bfr_reserve_eur", 0.0))
    security = safe_float(capital.get("security_reserve_eur", 0.0))

    protected_reserves = tax + security
    operating_reserves = bfr
    total_treasury = cash + tax + bfr + security

    transfers = funding.get("transfers", []) if isinstance(funding.get("transfers"), list) else []
    proposed_outflows = 0.0
    proposed_inflows = 0.0
    blocked = 0
    manual_review = 0

    for t in transfers:
        if not isinstance(t, dict):
            continue
        amount = safe_float(t.get("amount_eur", 0.0))
        status = t.get("status")

        if t.get("from_bucket") == "cash":
            proposed_outflows += amount
        if t.get("to_bucket") == "cash":
            proposed_inflows += amount
        if status == "blocked":
            blocked += 1
        if status == "manual_review_required":
            manual_review += 1

    cash_after_proposed = cash - proposed_outflows + proposed_inflows

    cash_weight = pct(cash, nav)
    protected_weight = pct(protected_reserves, nav)

    out = {
        "status": "ok",
        "engine": "treasury_state_engine_v1",
        "currency": "EUR",
        "capital_context": context,
        "nav_eur": round(nav, 2),
        "treasury": {
            "liquid_cash_eur": round(cash, 2),
            "tax_reserve_eur": round(tax, 2),
            "bfr_reserve_eur": round(bfr, 2),
            "security_reserve_eur": round(security, 2),
            "protected_reserves_eur": round(protected_reserves, 2),
            "operating_reserves_eur": round(operating_reserves, 2),
            "total_treasury_eur": round(total_treasury, 2)
        },
        "weights": {
            "cash_weight": cash_weight,
            "tax_reserve_weight": pct(tax, nav),
            "bfr_reserve_weight": pct(bfr, nav),
            "security_reserve_weight": pct(security, nav),
            "protected_reserve_weight": protected_weight,
            "total_treasury_weight": pct(total_treasury, nav)
        },
        "funding_impact": {
            "source": str(FUNDING_PLAN_PATH),
            "proposed_outflows_from_cash_eur": round(proposed_outflows, 2),
            "proposed_inflows_to_cash_eur": round(proposed_inflows, 2),
            "cash_after_proposed_eur": round(cash_after_proposed, 2),
            "manual_review_required": manual_review,
            "blocked_transfers": blocked
        },
        "health": {
            "treasury_health": classify_treasury_health(cash_weight, protected_weight),
            "cash_negative_after_proposed": cash_after_proposed < 0,
            "tax_reserve_protected": True,
            "security_reserve_protected": True,
            "bfr_available_for_operations": True
        },
        "governance": {
            "automatic_cash_transfer_allowed": bool(context.get("real_broker_funding_enabled", False)),
            "tax_reserve_can_fund_trading": False,
            "security_reserve_can_fund_trading": False,
            "manual_review_required": manual_review > 0 or blocked > 0
        },
        "ui": {
            "primary_headline": "Treasury Health",
            "primary_metric": classify_treasury_health(cash_weight, protected_weight),
            "secondary_metrics": {
                "cash_eur": round(cash, 2),
                "total_treasury_eur": round(total_treasury, 2),
                "tax_reserve_eur": round(tax, 2),
                "security_reserve_eur": round(security, 2)
            }
        },
        "updated_at": utc_now()
    }

    write_json(OUTPUT_PATH, out)
    append_jsonl(AUDIT_PATH, {
        "ts": utc_now(),
        "event": "treasury_state_updated",
        "treasury_health": out["health"]["treasury_health"],
        "total_treasury_eur": out["treasury"]["total_treasury_eur"],
        "cash_eur": out["treasury"]["liquid_cash_eur"]
    })

    return out


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
