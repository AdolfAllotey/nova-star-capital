from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
AUDIT_PATH = Path("data/capital/audit/capital_events.jsonl")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def build_capital_state() -> Dict[str, Any]:
    state = read_json(CAPITAL_STATE_PATH, default={}) or {}

    buckets = [
        "liquid_cash_eur",
        "tax_reserve_eur",
        "bfr_reserve_eur",
        "security_reserve_eur",
        "crypto_trading_eur",
        "crypto_lt_eur",
        "equities_offensive_eur",
        "equities_defensive_eur",
        "bonds_eur",
        "gold_eur",
        "options_eur"
    ]

    total_nav = sum(float(state.get(k, 0.0) or 0.0) for k in buckets)
    borrowed = float(state.get("borrowed_amount_eur", 0.0) or 0.0)

    collateral_value = (
        float(state.get("equities_offensive_eur", 0.0) or 0.0)
        + float(state.get("equities_defensive_eur", 0.0) or 0.0)
        + float(state.get("bonds_eur", 0.0) or 0.0)
        + float(state.get("gold_eur", 0.0) or 0.0)
    )

    state.update({
        "status": "ok",
        "engine": "capital_state_engine_v1",
        "currency": state.get("currency", "EUR"),
        "total_nav_eur": round(total_nav, 2),
        "collateral_value_eur": round(collateral_value, 2),
        "net_exposure_eur": round(total_nav - borrowed, 2),
        "updated_at": utc_now()
    })

    write_json(CAPITAL_STATE_PATH, state)
    append_jsonl(AUDIT_PATH, {
        "ts": utc_now(),
        "event": "capital_state_updated",
        "total_nav_eur": state["total_nav_eur"],
        "collateral_value_eur": state["collateral_value_eur"]
    })

    return state


if __name__ == "__main__":
    print(json.dumps(build_capital_state(), ensure_ascii=False, indent=2))
