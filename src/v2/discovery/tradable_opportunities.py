from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")

INPUT_PATH = DATA_DIR / "discovery" / "persistence_opportunities.json"
DISCOVERY_PATH = DATA_DIR / "discovery" / "discovery_candidates.json"
OUT_PATH = DATA_DIR / "discovery" / "tradable_opportunities.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    opp = load_json(INPUT_PATH, default={}) or {}
    disc = load_json(DISCOVERY_PATH, default={}) or {}

    opp_items = opp.get("items", [])
    disc_items = disc.get("items", [])

    tradable_by_symbol = {}

    if isinstance(disc_items, list):
        for row in disc_items:
            symbol = str(row.get("symbol") or "").upper().strip()
            if not symbol:
                continue

            sources = set(row.get("discovery_sources") or row.get("sources") or [])
            pair = str(row.get("pair") or "").upper().strip()

            is_tradable = (
                pair.endswith("USDT")
                and bool(sources.intersection({"binance", "mexc"}))
            )

            tradable_by_symbol[symbol] = {
                "tradable": is_tradable,
                "pair": pair,
                "sources": sorted(sources),
            }

    items = []

    if isinstance(opp_items, list):
        for row in opp_items:
            symbol = str(row.get("symbol") or "").upper().strip()
            info = tradable_by_symbol.get(symbol, {})

            if not info.get("tradable"):
                continue

            item = dict(row)
            item["tradable"] = True
            item["pair"] = info.get("pair") or item.get("pair") or f"{symbol}USDT"
            item["tradable_sources"] = info.get("sources") or []

            items.append(item)

    items.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

    payload = {
        "status": "ok",
        "generated_at": utc_now(),
        "engine": "tradable_opportunities_v1",
        "source": str(INPUT_PATH),
        "count": len(items),
        "items": items[:50],
    }

    save_json(OUT_PATH, payload)

    print({
        "output": str(OUT_PATH),
        "engine": "tradable_opportunities_v1",
        "count": len(items),
        "top": [x.get("symbol") for x in items[:10]],
    })


if __name__ == "__main__":
    main()
