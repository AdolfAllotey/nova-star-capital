from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

CRYPTO_INPUT_PATH = Path("/opt/nsc/app/data/long_term/funding_inputs/crypto.json")
OFF_INPUT_PATH = Path("/opt/nsc/app/data/long_term/funding_inputs/equities_offensive.json")

CRYPTO_TRADE_SIM_PATH = Path("/opt/nsc/data/preprod/trading/trade_simulation.json")
OFF_EQUITY_CURVE_PATH = Path("/opt/nsc/data/preprod/equities_offensive/reporting/equity_curve.json")
OFF_RECON_PATH = Path("/opt/nsc/app/data/equities_offensive/execution/reconciliation.json")
OFF_FILLS_PATH = Path("/opt/nsc/app/data/equities_offensive/execution/fills_simulated.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_float(v, default=None):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def sum_trade_like_pnl(payload):
    candidates = []

    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        for key in ("trades", "positions", "fills", "data", "rows", "items", "history"):
            if isinstance(payload.get(key), list):
                candidates = payload[key]
                break

    total = 0.0
    found = False

    for row in candidates:
        if not isinstance(row, dict):
            continue

        for field in (
            "realized_pnl_eur",
            "net_profit_eur",
            "profit_eur",
            "pnl_eur",
            "daily_profit",
            "daily_pnl",
            "pnl",
            "profit",
        ):
            value = safe_float(row.get(field))
            if value is not None:
                total += value
                found = True
                break

    return total if found else None


def collect_crypto_profit():
    payload = read_json(CRYPTO_TRADE_SIM_PATH, [])
    pnl = sum_trade_like_pnl(payload)
    if pnl is None:
        pnl = 0.0
    return {
        "net_profit_eur": max(float(pnl), 0.0),
        "source_file": str(CRYPTO_TRADE_SIM_PATH),
        "method": "sum_rows_realized_only",
    }


def collect_offensive_profit():
    curve = read_json(OFF_EQUITY_CURVE_PATH, {})
    if isinstance(curve, dict):
        breakdown = curve.get("breakdown", {}) or {}
        realized = safe_float(breakdown.get("realized_pnl"))
        if realized is not None:
            return {
                "net_profit_eur": max(float(realized), 0.0),
                "source_file": str(OFF_EQUITY_CURVE_PATH),
                "method": "equity_curve_breakdown_realized_only",
            }

    recon = read_json(OFF_RECON_PATH, {})
    if isinstance(recon, dict):
        summary = recon.get("summary", {}) or {}
        for field in ("realized_pnl_eur", "net_profit_eur", "profit_eur", "pnl_eur"):
            value = safe_float(summary.get(field))
            if value is not None:
                return {
                    "net_profit_eur": max(float(value), 0.0),
                    "source_file": str(OFF_RECON_PATH),
                    "method": f"reconciliation_summary_{field}",
                }

    fills = read_json(OFF_FILLS_PATH, [])
    pnl = sum_trade_like_pnl(fills)
    if pnl is not None:
        return {
            "net_profit_eur": max(float(pnl), 0.0),
            "source_file": str(OFF_FILLS_PATH),
            "method": "fills_sum_realized_only",
        }

    return {
        "net_profit_eur": 0.0,
        "source_file": str(OFF_EQUITY_CURVE_PATH),
        "method": "fallback_zero_realized_only",
    }


def update_input_file(path: Path, net_profit_eur: float, source_file: str | None, method: str):
    payload = read_json(path, {})
    if not isinstance(payload, dict):
        payload = {}

    payload["net_profit_eur"] = float(net_profit_eur)
    payload["profit_source_file"] = source_file
    payload["profit_collection_method"] = method
    payload["updated_at"] = utc_now()

    write_json(path, payload)


def main():
    crypto = collect_crypto_profit()
    offensive = collect_offensive_profit()

    update_input_file(
        CRYPTO_INPUT_PATH,
        crypto["net_profit_eur"],
        crypto["source_file"],
        crypto["method"],
    )
    update_input_file(
        OFF_INPUT_PATH,
        offensive["net_profit_eur"],
        offensive["source_file"],
        offensive["method"],
    )

    out = {
        "status": "ok",
        "engine": "long_term_profit_collector_v3",
        "results": {
            "crypto": crypto,
            "equities_offensive": offensive,
        },
        "updated_at": utc_now(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
