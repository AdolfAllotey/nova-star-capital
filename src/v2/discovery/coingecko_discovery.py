from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")
OUT = DATA_DIR / "market" / "coingecko_top_movers.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "accept": "application/json",
            "user-agent": "NovaStarCapital/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd"
        "&order=market_cap_desc"
        "&per_page=250"
        "&page=1"
        "&sparkline=false"
        "&price_change_percentage=1h,24h,7d"
    )

    rows = fetch_json(url)

    items: List[Dict[str, Any]] = []
    for r in rows:
        symbol = str(r.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        chg_24h = r.get("price_change_percentage_24h")
        price = r.get("current_price")

        try:
            chg_24h_f = float(chg_24h)
        except Exception:
            continue

        items.append({
            "id": r.get("id"),
            "symbol": symbol,
            "name": r.get("name") or symbol,
            "price": price,
            "chg_1h": r.get("price_change_percentage_1h_in_currency"),
            "chg_24h": chg_24h_f,
            "chg_7d": r.get("price_change_percentage_7d_in_currency"),
            "source": "coingecko",
            "pair": f"{symbol}USDT",
            "observation_only": True,
            "tradable": False,
            "preferred_exchange": None,
            "available_exchanges": [],
            "role": "external_market_discovery",
            "quote_asset": "USDT",
        })

    items.sort(key=lambda x: abs(float(x.get("chg_24h") or 0.0)), reverse=True)

    payload = {
        "status": "ok",
        "generated_at": utc_now(),
        "source": "coingecko",
        "count": len(items),
        "items": items[:100],
    }

    save_json(OUT, payload)
    print(json.dumps({"output": str(OUT), "count": len(payload["items"])}, indent=2))


if __name__ == "__main__":
    main()
