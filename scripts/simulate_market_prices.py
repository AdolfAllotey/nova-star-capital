from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

SRC = Path("/opt/nsc/app/data/market/prices.json")
OUT = Path("/opt/nsc/data/preprod/market_sim/prices_simulated.json")

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def main():
    raw = json.loads(SRC.read_text(encoding="utf-8"))

    prices = raw.get("prices") if isinstance(raw, dict) else {}
    if not isinstance(prices, dict):
        prices = {}

    clean = {}
    skipped = {}

    for symbol, price in prices.items():
        try:
            px = float(price)
            if px > 0:
                clean[str(symbol).upper()] = round(px, 4)
        except Exception:
            skipped[str(symbol)] = price

    payload = {
        "ts": now(),
        "engine": "market_sim_price_refresh_v1_schema_safe",
        "source": str(SRC),
        "prices": clean,
        "count": len(clean),
        "skipped": skipped,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "out": str(OUT),
        "count": len(clean),
        "skipped": len(skipped),
    }, indent=2))

if __name__ == "__main__":
    main()
