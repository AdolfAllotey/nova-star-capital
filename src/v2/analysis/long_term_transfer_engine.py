from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4


POSITIONS_PATH = Path("/opt/nsc/src/v2/data/long_term/long_term_positions.json")
TRANSFERS_PATH = Path("/opt/nsc/src/v2/data/long_term/long_term_transfers.json")
TARGETS_PATH = Path("/opt/nsc/src/v2/data/long_term/long_term_allocation_target.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def choose_target_symbol(targets: dict, bucket: str = "crypto_lt") -> str:
    bucket_targets = targets.get("targets", {}).get(bucket, {})
    if not bucket_targets:
        return "BTC"
    return max(bucket_targets.items(), key=lambda kv: kv[1])[0]


def append_transfer_flow(source_brick: str, symbol: str, amount_eur: float, quantity: float, flow_type: str = "profit_reallocation"):
    transfers = read_json(
        TRANSFERS_PATH,
        {
            "status": "ok",
            "engine": "long_term_transfers_v1",
            "currency": "EUR",
            "flows": [],
            "updated_at": None,
        },
    )

    flow = {
        "flow_id": f"ltf_{uuid4().hex[:12]}",
        "date": utc_now(),
        "flow_type": flow_type,
        "source_brick": source_brick,
        "target_bucket": "crypto_lt",
        "symbol": symbol,
        "amount_eur": amount_eur,
        "quantity": quantity,
        "execution_status": "executed",
        "custody_status": "active",
        "notes": f"Automatic transfer from {source_brick} to long term",
    }

    transfers.setdefault("flows", []).append(flow)
    transfers["updated_at"] = utc_now()
    write_json(TRANSFERS_PATH, transfers)
    return flow


def upsert_position(symbol: str, amount_eur: float, quantity: float, source_brick: str, custody_location: str = "Exchange"):
    positions = read_json(
        POSITIONS_PATH,
        {
            "status": "ok",
            "engine": "long_term_positions_v1",
            "currency": "EUR",
            "positions": [],
            "updated_at": None,
        },
    )

    rows = positions.setdefault("positions", [])
    symbol = symbol.upper().strip()
    existing = None

    for row in rows:
        if str(row.get("symbol", "")).upper() == symbol:
            existing = row
            break

    if existing is None:
        avg_cost = (amount_eur / quantity) if quantity > 0 else 0
        rows.append({
            "symbol": symbol,
            "asset_name": symbol,
            "asset_class": "crypto",
            "bucket": "crypto_lt",
            "quantity": quantity,
            "avg_cost_eur": avg_cost,
            "cost_basis_eur": amount_eur,
            "allocation_target_weight": None,
            "custody_type": "exchange_wallet" if custody_location.lower() == "exchange" else "cold_wallet",
            "custody_location": custody_location,
            "custody_status": "active",
            "source_bricks": [source_brick],
            "status": "ACTIVE",
        })
    else:
        prev_qty = float(existing.get("quantity") or 0)
        prev_cost = float(existing.get("cost_basis_eur") or 0)
        new_qty = prev_qty + quantity
        new_cost = prev_cost + amount_eur
        new_avg = (new_cost / new_qty) if new_qty > 0 else 0

        existing["quantity"] = new_qty
        existing["cost_basis_eur"] = new_cost
        existing["avg_cost_eur"] = new_avg

        srcs = existing.get("source_bricks") or []
        if source_brick not in srcs:
            srcs.append(source_brick)
        existing["source_bricks"] = srcs

    positions["updated_at"] = utc_now()
    write_json(POSITIONS_PATH, positions)


def simulate_buy_quantity(symbol: str, amount_eur: float) -> float:
    fake_prices = {
        "BTC": 68000,
        "ETH": 1850,
        "SOL": 120,
        "BNB": 520,
        "XRP": 0.60,
        "AVAX": 35,
        "MATIC": 0.95,
    }
    px = fake_prices.get(symbol.upper(), 1)
    return amount_eur / px if px > 0 else 0


def create_long_term_transfer(source_brick: str, amount_eur: float, symbol: str | None = None):
    targets = read_json(
        TARGETS_PATH,
        {
            "status": "ok",
            "engine": "long_term_allocation_target_v1",
            "targets": {"crypto_lt": {"BTC": 0.40}},
            "rebalance_threshold": 0.03,
            "updated_at": None,
        },
    )

    chosen_symbol = symbol.upper() if symbol else choose_target_symbol(targets, "crypto_lt")
    quantity = simulate_buy_quantity(chosen_symbol, amount_eur)

    flow = append_transfer_flow(
        source_brick=source_brick,
        symbol=chosen_symbol,
        amount_eur=amount_eur,
        quantity=quantity,
        flow_type="profit_reallocation",
    )

    upsert_position(
        symbol=chosen_symbol,
        amount_eur=amount_eur,
        quantity=quantity,
        source_brick=source_brick,
        custody_location="Exchange",
    )

    return {
        "status": "ok",
        "engine": "long_term_transfer_engine_v1",
        "flow": flow,
        "symbol": chosen_symbol,
        "amount_eur": amount_eur,
        "quantity": quantity,
        "updated_at": utc_now(),
    }


if __name__ == "__main__":
    result = create_long_term_transfer(source_brick="crypto", amount_eur=1000.0)
    print(json.dumps(result, ensure_ascii=False, indent=2))
