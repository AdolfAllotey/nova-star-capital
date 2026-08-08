from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/nsc/data/preprod")
SNAPSHOT = ROOT / "equities_offensive/universe/price_snapshot.json"
POSITIONS = ROOT / "equities_offensive/state/positions.json"
OUT = ROOT / "equities_offensive/market/prices.json"

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def main():
    current_prices = read_json(OUT, {}) or {}

    current_engine = str(
        current_prices.get("engine", "")
        if isinstance(current_prices, dict)
        else ""
    )

    current_source = str(
        current_prices.get("source", "")
        if isinstance(current_prices, dict)
        else ""
    ).lower()

    canonical_feed_active = (
        current_engine == "offensive_canonical_market_feed_v1"
        or current_source == "yfinance"
    )

    if canonical_feed_active:
        print({
            "status": "skipped",
            "reason": "canonical_market_feed_protected",
            "engine": current_engine,
            "source": current_source,
            "out": str(OUT),
        })
        return 0

    snap = read_json(SNAPSHOT, {}) or {}
    positions = read_json(POSITIONS, {}) or {}
    rows = snap.get("prices", {}) if isinstance(snap, dict) else {}

    day_seed = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
    prices = {}

    for sym, item in rows.items():
        sym = str(sym).upper()
        if not isinstance(item, dict):
            continue

        base = float(item.get("close") or 0)
        if sym in positions and isinstance(positions[sym], dict):
            avg = float(positions[sym].get("avg_price") or 0)
            if avg > 0:
                base = avg

        if base <= 0:
            continue

        wave = math.sin((day_seed + sum(ord(c) for c in sym)) / 7.0)
        drift = round(wave * 0.018, 6)
        prices[sym] = round(base * (1 + drift), 4)

    out = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "offensive_equity_simulator",
        "universe": "nasdaq_core",
        "prices": prices,
    }
    write_json(OUT, out)
    print({"saved": str(OUT), "count": len(prices), "source": "offensive_equity_simulator"})

if __name__ == "__main__":
    main()
