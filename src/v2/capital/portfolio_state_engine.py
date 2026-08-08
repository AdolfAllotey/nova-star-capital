from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
PORTFOLIO_TARGET_PATH = Path("/opt/nsc/data/preprod/portfolio/portfolio_target.json")

CRYPTO_POSITIONS_PATH = Path("/opt/nsc/data/preprod/trading/open_positions.json")
OFFENSIVE_POSITIONS_PATH = Path("data/equities_offensive/state/positions.json")
OFFENSIVE_REPORT_PATH = Path("data/equities_offensive/state/position_report.json")
LT_CRYPTO_PATH = Path("data/portfolio/lt_portfolio.json")
LT_EQUITIES_PATH = Path("data/portfolio/long_term_positions.json")

OUTPUT_PATH = Path("data/capital/portfolio_state.json")
AUDIT_PATH = Path("data/capital/audit/portfolio_state_events.jsonl")


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


def count_positions(doc: Any) -> int:
    if isinstance(doc, list):
        return len(doc)
    if isinstance(doc, dict):
        if isinstance(doc.get("positions"), list):
            return len(doc.get("positions") or [])
        return len(doc)
    return 0


def sum_crypto_positions_value(doc: Any) -> float:
    rows = doc if isinstance(doc, list) else []
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        total += safe_float(
            row.get("current_value_eur",
            row.get("market_value_eur",
            row.get("notional_eur",
            row.get("amount", 0.0))))
        )
    return total


def sum_lt_equities_value(doc: Any) -> float:
    positions = doc.get("positions", []) if isinstance(doc, dict) else []
    total = 0.0
    for row in positions:
        if not isinstance(row, dict):
            continue
        total += safe_float(row.get("market_value_eur", row.get("invested_eur", 0.0)))
    return total


def build_portfolio_state() -> Dict[str, Any]:
    capital = read_json(CAPITAL_STATE_PATH, default={}) or {}
    target = read_json(PORTFOLIO_TARGET_PATH, default={}) or {}

    crypto_positions = read_json(CRYPTO_POSITIONS_PATH, default=[]) or []
    offensive_positions = read_json(OFFENSIVE_POSITIONS_PATH, default={}) or {}
    offensive_report = read_json(OFFENSIVE_REPORT_PATH, default={}) or {}
    lt_crypto = read_json(LT_CRYPTO_PATH, default={}) or {}
    lt_equities = read_json(LT_EQUITIES_PATH, default={}) or {}

    nav = safe_float(capital.get("total_nav_eur", 0.0))
    target_weights = target.get("final_brick_weights", {}) if isinstance(target, dict) else {}

    crypto_value = sum_crypto_positions_value(crypto_positions)
    offensive_value = safe_float(offensive_report.get("total_notional_usd", 0.0))
    lt_crypto_value = safe_float(lt_crypto.get("total_value_eur", 0.0))
    lt_equities_value = sum_lt_equities_value(lt_equities)

    current_values = {
        "crypto_trading": round(crypto_value, 2),
        "crypto_lt": round(lt_crypto_value, 2),
        "equities_offensive": round(offensive_value, 2),
        "equities_lt": round(lt_equities_value, 2),
        "cash": round(safe_float(capital.get("liquid_cash_eur", 0.0)), 2),
        "tax_reserve": round(safe_float(capital.get("tax_reserve_eur", 0.0)), 2),
        "bfr_reserve": round(safe_float(capital.get("bfr_reserve_eur", 0.0)), 2),
        "security_reserve": round(safe_float(capital.get("security_reserve_eur", 0.0)), 2)
    }

    current_weights = {
        k: round(v / nav, 6) if nav > 0 else 0.0
        for k, v in current_values.items()
    }

    target_amounts = {
        k: round(nav * safe_float(v), 2)
        for k, v in target_weights.items()
    }

    drift = {
        k: round(current_weights.get(k, 0.0) - safe_float(target_weights.get(k, 0.0)), 6)
        for k in set(list(current_weights.keys()) + list(target_weights.keys()))
    }

    state = {
        "status": "ok",
        "engine": "portfolio_state_engine_v1",
        "currency": "EUR",
        "nav_eur": round(nav, 2),
        "sources": {
            "capital_state": str(CAPITAL_STATE_PATH),
            "portfolio_target": str(PORTFOLIO_TARGET_PATH),
            "crypto_positions": str(CRYPTO_POSITIONS_PATH),
            "offensive_positions": str(OFFENSIVE_POSITIONS_PATH),
            "offensive_report": str(OFFENSIVE_REPORT_PATH),
            "lt_crypto": str(LT_CRYPTO_PATH),
            "lt_equities": str(LT_EQUITIES_PATH)
        },
        "position_counts": {
            "crypto": count_positions(crypto_positions),
            "equities_offensive": count_positions(offensive_positions),
            "lt_equities": count_positions(lt_equities),
            "lt_crypto": count_positions((lt_crypto.get("positions") or {}) if isinstance(lt_crypto, dict) else {})
        },
        "target_weights": target_weights,
        "target_amounts_eur": target_amounts,
        "current_values_eur": current_values,
        "current_weights": current_weights,
        "drift": drift,
        "notes": [
            "V1 aggregates known runtime artifacts without executing transfers.",
            "Some values remain approximations until broker reconciliation is connected.",
            "Crypto trading and equities offensive are separated from LT pockets."
        ],
        "updated_at": utc_now()
    }

    write_json(OUTPUT_PATH, state)
    append_jsonl(AUDIT_PATH, {
        "ts": utc_now(),
        "event": "portfolio_state_updated",
        "nav_eur": state["nav_eur"],
        "position_counts": state["position_counts"]
    })

    return state


if __name__ == "__main__":
    print(json.dumps(build_portfolio_state(), ensure_ascii=False, indent=2))
