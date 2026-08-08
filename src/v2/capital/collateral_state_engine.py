from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
CAPITAL_CONTEXT_PATH = Path("data/capital/config/capital_context.json")
ENTERPRISE_VALUE_PATH = Path("data/capital/enterprise_value.json")
OUTPUT_PATH = Path("data/capital/collateral_state.json")
AUDIT_PATH = Path("data/capital/audit/collateral_events.jsonl")


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


def classify_ltv(ltv: float) -> str:
    if ltv <= 0.20:
        return "safe"
    if ltv <= 0.30:
        return "controlled"
    if ltv <= 0.35:
        return "upper_bound"
    return "danger"


def run() -> Dict[str, Any]:
    capital = read_json(CAPITAL_STATE_PATH, default={}) or {}
    context = read_json(CAPITAL_CONTEXT_PATH, default={}) or {}
    enterprise = read_json(ENTERPRISE_VALUE_PATH, default={}) or {}

    nav = safe_float(capital.get("total_nav_eur", 0.0))
    debt = safe_float(capital.get("borrowed_amount_eur", 0.0))

    eligible_assets = {
        "equities_offensive_eur": safe_float(capital.get("equities_offensive_eur", 0.0)),
        "equities_defensive_eur": safe_float(capital.get("equities_defensive_eur", 0.0)),
        "bonds_eur": safe_float(capital.get("bonds_eur", 0.0)),
        "gold_eur": safe_float(capital.get("gold_eur", 0.0))
    }

    ineligible_assets = {
        "crypto_trading_eur": safe_float(capital.get("crypto_trading_eur", 0.0)),
        "crypto_lt_eur": safe_float(capital.get("crypto_lt_eur", 0.0)),
        "tax_reserve_eur": safe_float(capital.get("tax_reserve_eur", 0.0)),
        "security_reserve_eur": safe_float(capital.get("security_reserve_eur", 0.0))
    }

    eligible_value = sum(eligible_assets.values())
    ineligible_value = sum(ineligible_assets.values())
    ltv = pct(debt, eligible_value)

    start_capacity = eligible_value * 0.25
    mature_capacity = eligible_value * 0.35

    out = {
        "status": "ok",
        "engine": "collateral_state_engine_v1",
        "currency": "EUR",
        "capital_context": context,
        "nav_eur": round(nav, 2),
        "eligible_collateral_value_eur": round(eligible_value, 2),
        "ineligible_collateral_value_eur": round(ineligible_value, 2),
        "borrowed_amount_eur": round(debt, 2),
        "ltv_current": ltv,
        "ltv_status": classify_ltv(ltv),
        "capacity": {
            "start_ltv_25_capacity_eur": round(start_capacity, 2),
            "mature_ltv_35_capacity_eur": round(mature_capacity, 2),
            "remaining_start_capacity_eur": round(max(0.0, start_capacity - debt), 2),
            "remaining_mature_capacity_eur": round(max(0.0, mature_capacity - debt), 2)
        },
        "eligible_assets": {k: round(v, 2) for k, v in eligible_assets.items()},
        "ineligible_assets": {k: round(v, 2) for k, v in ineligible_assets.items()},
        "rules": {
            "crypto_collateral_allowed": False,
            "tax_reserve_collateral_allowed": False,
            "security_reserve_collateral_allowed": False,
            "debt_must_finance_productive_assets_only": True,
            "structural_ltv_limit": 0.35
        },
        "risk_flags": {
            "ltv_above_25": ltv > 0.25,
            "ltv_above_35": ltv > 0.35,
            "eligible_collateral_missing": eligible_value <= 0,
            "debt_without_collateral": debt > 0 and eligible_value <= 0
        },
        "governance": {
            "new_debt_allowed": bool(context.get("real_debt_enabled", False)) and eligible_value > 0 and ltv <= 0.25,
            "requires_review": ltv > 0.25 or debt > 0,
            "hard_block_new_debt": (not bool(context.get("real_debt_enabled", False))) or ltv > 0.35 or (debt > 0 and eligible_value <= 0)
        },
        "enterprise_value_reference": {
            "net_value_eur": ((enterprise.get("enterprise_value") or {}).get("net_value_eur")),
            "source": str(ENTERPRISE_VALUE_PATH)
        },
        "updated_at": utc_now()
    }

    write_json(OUTPUT_PATH, out)
    append_jsonl(AUDIT_PATH, {
        "ts": utc_now(),
        "event": "collateral_state_updated",
        "eligible_collateral_value_eur": out["eligible_collateral_value_eur"],
        "ltv_current": out["ltv_current"],
        "ltv_status": out["ltv_status"]
    })

    return out


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
