from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

DST = Path("/opt/nsc/data/preprod/equities_offensive/market/prices.json")
SNAPSHOT = Path("/opt/nsc/data/preprod/equities_offensive/universe/price_snapshot.json")

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def normalize_prices(doc):
    prices = doc.get("prices", {}) if isinstance(doc, dict) else {}
    out = {}
    for k, v in prices.items():
        try:
            px = float(v)
            if px > 0:
                out[str(k).upper()] = px
        except Exception:
            pass
    return out

def main():
    current_doc = read_json(DST, {}) or {}
    snapshot_doc = read_json(SNAPSHOT, {}) or {}

    current_engine = str(
        current_doc.get("engine", "")
        if isinstance(current_doc, dict)
        else ""
    )

    current_source = str(
        current_doc.get("source", "")
        if isinstance(current_doc, dict)
        else ""
    ).lower()

    snapshot_engine = str(
        snapshot_doc.get("engine", "")
        if isinstance(snapshot_doc, dict)
        else ""
    )

    snapshot_source = str(
        snapshot_doc.get("source", "")
        if isinstance(snapshot_doc, dict)
        else ""
    ).lower()

    canonical_feed_active = (
        current_engine == "offensive_canonical_market_feed_v1"
        or snapshot_engine == "offensive_canonical_snapshot_v1"
        or current_source == "yfinance"
        or snapshot_source == "yfinance"
    )

    if canonical_feed_active:
        print({
            "status": "skipped",
            "reason": "canonical_market_feed_protected",
            "prices_engine": current_engine,
            "prices_source": current_source,
            "snapshot_engine": snapshot_engine,
            "snapshot_source": snapshot_source,
        })
        return 0

    equity_prices = normalize_prices(current_doc)

    rows = snapshot_doc.get("prices", {}) if isinstance(snapshot_doc, dict) else {}
    snapshot_prices = {}
    refreshed_snapshot = {}

    for sym, item in rows.items():
        key = str(sym).upper()
        if isinstance(item, dict):
            row = dict(item)
            try:
                fallback_close = float(row.get("close") or 0)
                if fallback_close > 0:
                    snapshot_prices[key] = fallback_close
            except Exception:
                pass

            if key in equity_prices:
                row["close"] = equity_prices[key]

            refreshed_snapshot[key] = row

    merged = dict(snapshot_prices)
    merged.update(equity_prices)

    out = {
        "ts": utc_now_iso(),
        "engine": "equ_prices_sync_v2_equity_only",
        "source": current_doc.get("source", "offensive_equity_simulator") if isinstance(current_doc, dict) else "offensive_equity_simulator",
        "universe": "nasdaq_core",
        "prices": merged,
        "snapshot_count": len(snapshot_prices),
        "equity_price_count": len(equity_prices),
        "crypto_merge": False
    }

    write_json(DST, out)

    write_json(SNAPSHOT, {
        "ts": utc_now_iso(),
        "engine": "equ_prices_sync_v2_snapshot_bridge",
        "prices": refreshed_snapshot,
        "synced_from": str(DST)
    })

    print({"saved": str(DST), "count": len(merged), "crypto_merge": False})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
