from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

try:
    import ccxt
except Exception:
    ccxt = None


SRC_CANDIDATES = [
    Path("/opt/nsc/src/v2/data/crypto_long_term.json"),
    Path("/opt/nsc/app/src/v2/data/crypto_long_term.json"),
]

OUT_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_source() -> Path:
    for p in SRC_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("crypto_long_term.json not found")


def extract_positions(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("positions", "holdings", "assets", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def normalize_symbol(row: dict) -> str:
    return str(row.get("symbol") or row.get("asset") or row.get("token") or "").upper().strip()


def get_qty(row: dict) -> float:
    for key in ("quantity", "qty", "amount"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)
            except Exception:
                return 0.0
    return 0.0


def get_avg_cost_eur(row: dict) -> float | None:
    for key in ("avg_cost_eur", "avg_cost", "price_avg", "entry_price"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)
            except Exception:
                return None
    return None


def get_cost_basis_eur(row: dict, qty: float, avg_cost_eur: float | None) -> float | None:
    for key in ("cost_basis_eur", "invested_eur", "cost_basis"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)
            except Exception:
                return None
    if avg_cost_eur is not None:
        return qty * avg_cost_eur
    return None


def map_to_market_symbol(symbol: str) -> str | None:
    mapping = {
        "BTC": "BTC/USDT",
        "ETH": "ETH/USDT",
        "SOL": "SOL/USDT",
        "BNB": "BNB/USDT",
        "XRP": "XRP/USDT",
        "AVAX": "AVAX/USDT",
        "MATIC": "MATIC/USDT",
    }
    return mapping.get(symbol)


def get_usdt_eur_rate(exchange) -> float:
    direct_pairs = ["USDT/EUR", "EUR/USDT"]
    for pair in direct_pairs:
        try:
            ticker = exchange.fetch_ticker(pair)
            last = float(ticker["last"])
            if last > 0:
                if pair == "USDT/EUR":
                    return last
                return 1 / last
        except Exception:
            continue
    return 0.92


def fetch_prices(symbols: list[str]) -> dict[str, float]:
    prices = {}
    if ccxt is None:
        return prices

    ex = ccxt.binance({"enableRateLimit": True})
    eur_rate = get_usdt_eur_rate(ex)

    for symbol in symbols:
        eur_market = f"{symbol}/EUR"
        usdt_market = map_to_market_symbol(symbol)

        # 1) try direct EUR pair first
        try:
            ticker = ex.fetch_ticker(eur_market)
            last_eur = float(ticker["last"])
            if last_eur > 0:
                prices[symbol] = last_eur
                continue
        except Exception:
            pass

        # 2) fallback to USDT pair
        if usdt_market:
            try:
                ticker = ex.fetch_ticker(usdt_market)
                last_usdt = float(ticker["last"])
                if last_usdt > 0:
                    prices[symbol] = last_usdt * eur_rate
                    continue
            except Exception:
                pass

    return prices


def main():
    src = find_source()
    payload = read_json(src)
    positions = extract_positions(payload)

    symbols = [normalize_symbol(r) for r in positions if normalize_symbol(r)]
    prices = fetch_prices(symbols)

    out_positions = []
    total_market_value = 0.0
    total_cost_basis = 0.0
    cold_storage_value = 0.0

    for row in positions:
        symbol = normalize_symbol(row)
        qty = get_qty(row)
        avg_cost_eur = get_avg_cost_eur(row)
        cost_basis_eur = get_cost_basis_eur(row, qty, avg_cost_eur)
        last_price_eur = prices.get(symbol)
        market_value_eur = qty * last_price_eur if last_price_eur is not None else None
        unrealized_pnl_eur = (
            market_value_eur - cost_basis_eur
            if market_value_eur is not None and cost_basis_eur is not None
            else None
        )

        custody = str(
            row.get("custody_location")
            or row.get("custody_type")
            or row.get("wallet")
            or row.get("location")
            or ""
        ).lower()

        if market_value_eur is not None:
            total_market_value += market_value_eur
        if cost_basis_eur is not None:
            total_cost_basis += cost_basis_eur
        if market_value_eur is not None and any(x in custody for x in ("ledger", "cold", "wallet")):
            cold_storage_value += market_value_eur

        out_positions.append({
            "symbol": symbol,
            "asset_name": row.get("asset_name") or symbol,
            "asset_class": row.get("asset_class") or row.get("type") or "crypto",
            "bucket": row.get("bucket") or "crypto_lt",
            "quantity": qty,
            "avg_cost_eur": avg_cost_eur,
            "cost_basis_eur": cost_basis_eur,
            "last_price_eur": last_price_eur,
            "market_value_eur": market_value_eur,
            "unrealized_pnl_eur": unrealized_pnl_eur,
            "custody_type": row.get("custody_type"),
            "custody_location": row.get("custody_location") or row.get("wallet") or row.get("location"),
            "custody_status": row.get("custody_status") or row.get("status"),
            "source_bricks": row.get("source_bricks") or [],
            "last_price_update": utc_now(),
        })

    total_pnl = total_market_value - total_cost_basis if total_market_value and total_cost_basis else None
    total_pnl_pct = (total_pnl / total_cost_basis) if total_pnl is not None and total_cost_basis > 0 else None
    cold_ratio = (cold_storage_value / total_market_value) if total_market_value > 0 else None

    result = {
        "status": "ok",
        "engine": "long_term_valuation_v1",
        "source_file": str(src),
        "currency": "EUR",
        "totals": {
            "market_value_eur": total_market_value,
            "cost_basis_eur": total_cost_basis,
            "unrealized_pnl_eur": total_pnl,
            "unrealized_pnl_pct": total_pnl_pct,
            "assets_count": len(out_positions),
            "cold_storage_ratio": cold_ratio,
        },
        "positions": out_positions,
        "updated_at": utc_now(),
    }

    write_json(OUT_PATH, result)
    print(str(OUT_PATH))


if __name__ == "__main__":
    main()
