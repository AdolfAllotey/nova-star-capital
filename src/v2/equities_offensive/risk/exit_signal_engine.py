#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import os

ROOT = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

POSITIONS_PATH = ROOT / "equities_offensive/state/positions.json"
PRICES_PATH = ROOT / "equities_offensive/market/prices.json"
OUT_PATH = ROOT / "equities_offensive/risk/exit_candidates.json"

TP_PCT = 0.10
SL_PCT = -0.05


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def normalize_positions(raw):
    out = []

    if isinstance(raw, dict):
        for symbol, pos in raw.items():
            if not isinstance(pos, dict):
                continue
            row = dict(pos)
            row["symbol"] = row.get("symbol") or symbol
            out.append(row)
        return out

    if isinstance(raw, list):
        for pos in raw:
            if not isinstance(pos, dict):
                continue
            symbol = pos.get("symbol") or pos.get("ticker") or pos.get("asset")
            if not symbol:
                continue
            row = dict(pos)
            row["symbol"] = symbol
            out.append(row)
        return out

    return out


def main():
    positions_raw = load_json(POSITIONS_PATH)
    prices_doc = load_json(PRICES_PATH)

    if isinstance(prices_doc, dict) and isinstance(prices_doc.get("prices"), dict):
        prices = prices_doc.get("prices") or {}
    else:
        prices = prices_doc if isinstance(prices_doc, dict) else {}

    positions = normalize_positions(positions_raw)
    candidates = []

    for pos in positions:
        symbol = str(pos.get("symbol", "")).strip().upper()
        if not symbol:
            continue

        try:
            qty = float(pos.get("qty", 0) or 0)
            avg_price = float(pos.get("avg_price", 0) or 0)
        except Exception:
            continue

        if qty <= 0 or avg_price <= 0:
            continue

        price = prices.get(symbol)
        if price is None:
            price = prices.get(symbol.upper())
        if price is None:
            continue

        try:
            price = float(price)
        except Exception:
            continue

        pnl_pct = (price - avg_price) / avg_price

        if pnl_pct >= TP_PCT:
            candidates.append({
                "symbol": symbol,
                "side": "SELL",
                "qty": qty,
                "type": "MKT",
                "score": 1.0,
                "reason": f"take_profit_{round(pnl_pct * 100, 2)}%"
            })
        elif pnl_pct <= SL_PCT:
            candidates.append({
                "symbol": symbol,
                "side": "SELL",
                "qty": qty,
                "type": "MKT",
                "score": 1.0,
                "reason": f"stop_loss_{round(pnl_pct * 100, 2)}%"
            })

    out = {
        "ts": utc_now(),
        "positions_input_type": type(positions_raw).__name__,
        "positions_count": len(positions),
        "candidates": candidates
    }

    save_json(OUT_PATH, out)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
