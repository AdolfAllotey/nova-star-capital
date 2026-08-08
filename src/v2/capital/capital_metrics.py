from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
OUTPUT_PATH = Path("data/capital/capital_metrics.json")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pct(part: float, total: float) -> float:
    return round(part / total, 6) if total else 0.0


def run() -> Dict[str, Any]:
    state = read_json(CAPITAL_STATE_PATH, default={}) or {}
    nav = float(state.get("total_nav_eur", 0.0) or 0.0)

    metrics = {
        "status": "ok",
        "engine": "capital_metrics_v1",
        "nav_eur": nav,
        "weights": {
            "cash": pct(float(state.get("liquid_cash_eur", 0.0) or 0.0), nav),
            "crypto_trading": pct(float(state.get("crypto_trading_eur", 0.0) or 0.0), nav),
            "crypto_lt": pct(float(state.get("crypto_lt_eur", 0.0) or 0.0), nav),
            "equities": pct(
                float(state.get("equities_offensive_eur", 0.0) or 0.0)
                + float(state.get("equities_defensive_eur", 0.0) or 0.0),
                nav
            ),
            "bonds": pct(float(state.get("bonds_eur", 0.0) or 0.0), nav),
            "gold": pct(float(state.get("gold_eur", 0.0) or 0.0), nav)
        },
        "collateral_value_eur": state.get("collateral_value_eur", 0.0),
        "borrowed_amount_eur": state.get("borrowed_amount_eur", 0.0)
    }

    write_json(OUTPUT_PATH, metrics)
    return metrics


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
