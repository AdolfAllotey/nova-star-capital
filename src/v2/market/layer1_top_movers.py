import json
import os
from datetime import datetime, timezone
import requests
from pathlib import Path

BASE = Path("/opt/nsc/src/v2")
DATA_DIR = BASE / "data" / "market"
OUTPUT_FILE = DATA_DIR / "top_movers_layer1.json"
UNIVERSE_FILE = DATA_DIR / "layer1_universe.json"

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{}"

def load_universe():
    try:
        with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)["tokens"]
    except Exception as e:
        return []

def fetch_token_data(token_id):
    try:
        url = COINGECKO_URL.format(token_id)
        resp = requests.get(url, timeout=10)
        data = resp.json()

        market = data.get("market_data", {})

        return {
            "id": token_id,
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name", ""),
            "price_usd": market.get("current_price", {}).get("usd", 0),
            "change_30d": market.get("price_change_percentage_30d_in_currency", {}).get("usd", 0),
            "market_cap": market.get("market_cap", {}).get("usd", 0),
            "volume_24h": market.get("total_volume", {}).get("usd", 0)
        }

    except Exception:
        return None

def compute_score(item):
    """Très simple pour la préprod, ajustable ensuite"""
    change = max(item["change_30d"], 0)
    vol = item["volume_24h"]
    mcap = item["market_cap"]

    return (
        0.6 * (change / 100) +
        0.25 * min(vol / 500000000, 1) +   # normalisation
        0.15 * min(mcap / 20000000000, 1)
    )

def main():
    universe = load_universe()
    results = []

    for token in universe:
        item = fetch_token_data(token["id"])
        if not item:
            continue

        # filtres de base
        if item["volume_24h"] < 2000000:
            continue

        item["score_layer1"] = round(compute_score(item), 4)
        results.append(item)

    results = sorted(results, key=lambda x: x["change_30d"], reverse=True)

    out = {
        "universe": "layer1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": results
    }

    OUTPUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[layer1_top_movers] OK - updated", OUTPUT_FILE)

if __name__ == "__main__":
    main()
