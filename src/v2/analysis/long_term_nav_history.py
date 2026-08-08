from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

VALUATION_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json")
OUT_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_nav_history.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    valuation = read_json(VALUATION_PATH)
    if not valuation:
        raise FileNotFoundError(f"Missing valuation file: {VALUATION_PATH}")

    totals = valuation.get("totals", {})
    entry = {
        "ts": utc_now(),
        "market_value_eur": totals.get("market_value_eur"),
        "cost_basis_eur": totals.get("cost_basis_eur"),
        "unrealized_pnl_eur": totals.get("unrealized_pnl_eur"),
        "unrealized_pnl_pct": totals.get("unrealized_pnl_pct"),
        "assets_count": totals.get("assets_count"),
        "cold_storage_ratio": totals.get("cold_storage_ratio"),
    }

    existing = read_json(OUT_PATH)
    if not isinstance(existing, dict):
        existing = {"status": "ok", "engine": "long_term_nav_history_v1", "history": []}

    history = existing.get("history", [])
    if not isinstance(history, list):
        history = []

    history.append(entry)
    history = history[-1000:]

    out = {
        "status": "ok",
        "engine": "long_term_nav_history_v1",
        "history": history,
        "updated_at": utc_now(),
    }
    write_json(OUT_PATH, out)
    print(str(OUT_PATH))


if __name__ == "__main__":
    main()
