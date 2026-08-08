from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")
OUT = DATA_DIR / "market" / "coinmarketcap_top_movers.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_json(url: str, api_key: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-CMC_PRO_API_KEY": api_key,
            "User-Agent": "NovaStarCapital/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    api_key = os.getenv("CMC_API_KEY") or os.getenv("COINMARKETCAP_API_KEY")

    if not api_key:
        payload = {
            "status": "missing_api_key",
            "updated_at": utc_now(),
            "source": "coinmarketcap",
            "items": [],
            "message": "Set CMC_API_KEY or COINMARKETCAP_API_KEY in /etc/nsc/preprod.env",
        }
        save_json(OUT, payload)
        print({"output": str(OUT), "status": "missing_api_key", "count": 0})
        return

    url = (
        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        "?start=1&limit=200&convert=USD&sort=percent_change_24h&sort_dir=desc"
    )

    raw = fetch_json(url, api_key)
    rows = raw.get("data", []) if isinstance(raw, dict) else []

    items = []
    for row in rows:
        quote = ((row.get("quote") or {}).get("USD") or {})
        symbol = str(row.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        chg_24h = quote.get("percent_change_24h")
        try:
            chg_24h = float(chg_24h)
        except Exception:
            continue

        items.append({
            "id": row.get("id"),
            "symbol": symbol,
            "name": row.get("name") or symbol,
            "price": quote.get("price"),
            "chg_1h": quote.get("percent_change_1h"),
            "chg_24h": round(chg_24h, 6),
            "chg_7d": quote.get("percent_change_7d"),
            "source": "coinmarketcap",
            "pair": f"{symbol}USDT",
            "observation_only": True,
            "tradable": False,
            "preferred_exchange": None,
            "available_exchanges": [],
            "role": "external_market_discovery",
            "quote_asset": "USDT",
        })

    payload = {
        "status": "ok",
        "updated_at": utc_now(),
        "source": "coinmarketcap",
        "items": items,
    }

    save_json(OUT, payload)
    print({"output": str(OUT), "status": "ok", "count": len(items)})


if __name__ == "__main__":
    main()
