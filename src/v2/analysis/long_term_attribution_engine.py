from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


POSITIONS_PATH = Path("/opt/nsc/src/v2/data/long_term/long_term_positions.json")
VALUATION_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json")
OUT_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_attribution.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def main():
    positions_payload = read_json(POSITIONS_PATH, {"positions": []}) or {"positions": []}
    valuation_payload = read_json(VALUATION_PATH, {"positions": [], "totals": {}}) or {"positions": [], "totals": {}}

    positions = positions_payload.get("positions", []) if isinstance(positions_payload, dict) else []
    valuations = valuation_payload.get("positions", []) if isinstance(valuation_payload, dict) else []
    totals = valuation_payload.get("totals", {}) if isinstance(valuation_payload, dict) else {}

    valuation_by_symbol = {}
    for row in valuations:
        symbol = str(row.get("symbol") or "").upper()
        if symbol:
            valuation_by_symbol[symbol] = row

    by_brick = {}
    by_asset = {}

    for pos in positions:
        symbol = str(pos.get("symbol") or "").upper()
        if not symbol:
            continue

        valuation = valuation_by_symbol.get(symbol, {})
        invested = safe_float(pos.get("cost_basis_eur"))
        market_value = safe_float(valuation.get("market_value_eur"))
        pnl = safe_float(valuation.get("unrealized_pnl_eur"), None)
        if pnl is None:
            pnl = market_value - invested

        source_bricks = pos.get("source_bricks") or []
        if not isinstance(source_bricks, list):
            source_bricks = []

        asset_entry = {
            "symbol": symbol,
            "asset_name": pos.get("asset_name") or symbol,
            "asset_class": pos.get("asset_class") or "unknown",
            "bucket": pos.get("bucket") or "long_term",
            "invested_eur": invested,
            "market_value_eur": market_value,
            "pnl_eur": pnl,
            "pnl_pct": (pnl / invested) if invested > 0 else None,
            "source_bricks": source_bricks,
        }
        by_asset[symbol] = asset_entry

        if not source_bricks:
            source_bricks = ["unknown"]

        split_invested = invested / len(source_bricks) if source_bricks else invested
        split_value = market_value / len(source_bricks) if source_bricks else market_value
        split_pnl = pnl / len(source_bricks) if source_bricks else pnl

        for brick in source_bricks:
            if brick not in by_brick:
                by_brick[brick] = {
                    "brick": brick,
                    "invested_eur": 0.0,
                    "market_value_eur": 0.0,
                    "pnl_eur": 0.0,
                    "assets": [],
                }

            by_brick[brick]["invested_eur"] += split_invested
            by_brick[brick]["market_value_eur"] += split_value
            by_brick[brick]["pnl_eur"] += split_pnl
            if symbol not in by_brick[brick]["assets"]:
                by_brick[brick]["assets"].append(symbol)

    total_value = safe_float(totals.get("market_value_eur"))
    total_invested = safe_float(totals.get("cost_basis_eur"))
    total_pnl = safe_float(totals.get("unrealized_pnl_eur"), None)
    if total_pnl is None:
        total_pnl = total_value - total_invested

    for brick, row in by_brick.items():
        invested = safe_float(row.get("invested_eur"))
        value = safe_float(row.get("market_value_eur"))
        pnl = safe_float(row.get("pnl_eur"))
        row["pnl_pct"] = (pnl / invested) if invested > 0 else None
        row["weight_in_lt"] = (value / total_value) if total_value > 0 else None
        row["contribution_to_total_pnl"] = (pnl / total_pnl) if total_pnl not in (0, None) else None

    for symbol, row in by_asset.items():
        value = safe_float(row.get("market_value_eur"))
        pnl = safe_float(row.get("pnl_eur"))
        row["weight_in_lt"] = (value / total_value) if total_value > 0 else None
        row["contribution_to_total_pnl"] = (pnl / total_pnl) if total_pnl not in (0, None) else None

    result = {
        "status": "ok",
        "engine": "long_term_attribution_engine_v1",
        "totals": {
            "market_value_eur": total_value,
            "cost_basis_eur": total_invested,
            "unrealized_pnl_eur": total_pnl,
            "unrealized_pnl_pct": (total_pnl / total_invested) if total_invested > 0 else None,
        },
        "by_brick": by_brick,
        "by_asset": by_asset,
        "updated_at": utc_now(),
    }

    write_json(OUT_PATH, result)
    print(str(OUT_PATH))


if __name__ == "__main__":
    main()
