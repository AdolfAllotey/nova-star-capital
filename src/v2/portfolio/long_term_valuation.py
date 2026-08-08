import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request


PORTFOLIO_PATH = Path("/opt/nsc/app/data/portfolio/lt_portfolio.json")
OUTPUT_PATH = Path("/opt/nsc/app/data/portfolio/lt_portfolio_valuation.json")

PRICE_MAP = {
    "BTC": "BTCEUR",
    "ETH": "ETHEUR",
    "SOL": "SOLEUR",
}

FALLBACK_PRICES = {
    "BTC": 60000.0,
    "ETH": 3000.0,
    "SOL": 150.0,
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_binance_price(symbol_code: str):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_code}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return float(data["price"])


def get_price(asset: str):
    try:
        return fetch_binance_price(PRICE_MAP[asset]), "binance"
    except Exception:
        return FALLBACK_PRICES[asset], "fallback"


def main():
    portfolio = read_json(PORTFOLIO_PATH, default={}) or {}
    positions = portfolio.get("positions", {}) or {}

    enriched = {}
    total_invested = 0.0
    total_market_value = 0.0

    for asset, pos in positions.items():
        invested = float(pos.get("invested_eur", pos.get("amount_eur", 0.0)) or 0.0)
        units = float(pos.get("units", 0.0) or 0.0)
        avg_price = float(pos.get("avg_price_eur", 0.0) or 0.0)

        current_price, price_source = get_price(asset)
        market_value = units * current_price
        pnl_eur = market_value - invested
        pnl_pct = (pnl_eur / invested) if invested > 0 else 0.0

        enriched[asset] = {
            "invested_eur": round(invested, 6),
            "units": round(units, 10),
            "avg_price_eur": round(avg_price, 6),
            "current_price_eur": round(current_price, 6),
            "market_value_eur": round(market_value, 6),
            "pnl_eur": round(pnl_eur, 6),
            "pnl_pct": round(pnl_pct, 6),
            "price_source": price_source,
        }

        total_invested += invested
        total_market_value += market_value

    total_pnl = total_market_value - total_invested
    total_pnl_pct = (total_pnl / total_invested) if total_invested > 0 else 0.0

    out = {
        "status": "ok",
        "engine": "long_term_valuation_v1",
        "positions": enriched,
        "totals": {
            "invested_eur": round(total_invested, 6),
            "market_value_eur": round(total_market_value, 6),
            "pnl_eur": round(total_pnl, 6),
            "pnl_pct": round(total_pnl_pct, 6),
        },
        "timestamp": utc_now(),
    }

    write_json(OUTPUT_PATH, out)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
