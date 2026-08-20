#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

DATA_ROOT = Path(os.environ.get("NSC_DATA_ROOT") or os.environ.get("NSC_DATA_DIR") or "/opt/nsc/data/preprod")
MARKET_DIR = DATA_ROOT / "market"

BINANCE_MOVERS_PATH = MARKET_DIR / "top_movers.json"
EXTERNAL_MOVERS_PATH = MARKET_DIR / "top_movers_external.json"
OUT_PATH = MARKET_DIR / "top_movers_combined.json"
TOKEN_EXCHANGE_MAP_PATH = DATA_ROOT / "config" / "token_exchange_map.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def norm_symbol(item: Dict[str, Any]) -> str:
    return str(item.get("symbol") or item.get("token") or "").upper().replace("USDT", "").strip()


def exchange_info(symbol: str, exchange_map: Dict[str, Any]) -> Dict[str, Any]:
    info = exchange_map.get(symbol) or exchange_map.get(symbol.upper()) or exchange_map.get(symbol.lower()) or {}
    if isinstance(info, str):
        return {
            "tradable": True,
            "preferred_exchange": info.lower(),
            "available_exchanges": [info.lower()],
            "role": "unknown",
            "quote_asset": "USDT",
        }
    if isinstance(info, dict):
        preferred = info.get("preferred_exchange") or info.get("exchange") or info.get("venue")
        available = info.get("available_exchanges") or ([preferred] if preferred else [])
        return {
            "tradable": bool(preferred or available),
            "preferred_exchange": preferred,
            "available_exchanges": available,
            "role": info.get("role", "unknown"),
            "quote_asset": info.get("quote_asset", "USDT"),
        }
    return {
        "tradable": False,
        "preferred_exchange": None,
        "available_exchanges": [],
        "role": "unknown",
        "quote_asset": "USDT",
    }


def normalize_item(item: Dict[str, Any], default_source: str, exchange_map: Dict[str, Any]) -> Dict[str, Any] | None:
    symbol = norm_symbol(item)
    if not symbol:
        return None

    ex = exchange_info(symbol, exchange_map)

    # RC2 Market Integrity Gate V1:
    # A Binance pair is eligible for execution fallback only when the
    # upstream market source explicitly certified STATUS=TRADING.
    #
    # `source=binance + pair` alone is not evidence of tradability:
    # Binance ticker/24hr can expose suspended / BREAK markets.
    if (
        not ex.get("tradable")
        and item.get("source") == "binance"
        and item.get("pair")
        and str(item.get("market_status") or "").upper() == "TRADING"
        and item.get("spot_trading_allowed") is True
    ):
        ex = {
            "tradable": True,
            "preferred_exchange": "binance",
            "available_exchanges": ["binance"],
            "role": "altcoin_trading",
            "quote_asset": "USDT",
        }

    pair = item.get("pair") or (f"{symbol}{ex.get('quote_asset') or 'USDT'}" if ex.get("tradable") else None)

    return {
        "id": str(item.get("id") or symbol.lower()),
        "symbol": symbol,
        "name": item.get("name") or symbol,
        "price": item.get("price"),
        "chg_1h": item.get("chg_1h"),
        "chg_24h": item.get("chg_24h"),
        "chg_7d": item.get("chg_7d"),
        "source": item.get("source") or default_source,
        "pair": pair,
        "market_status": item.get("market_status"),
        "spot_trading_allowed": item.get(
            "spot_trading_allowed"
        ),
        "ticker_close_time": item.get(
            "ticker_close_time"
        ),
        "observation_only": bool(item.get("observation_only", False)),
        "tradable": bool(ex.get("tradable")),
        "preferred_exchange": ex.get("preferred_exchange"),
        "available_exchanges": ex.get("available_exchanges", []),
        "role": ex.get("role", "unknown"),
        "quote_asset": ex.get("quote_asset", "USDT"),
    }


def main() -> int:
    exchange_map = load_json(TOKEN_EXCHANGE_MAP_PATH, {})
    if not isinstance(exchange_map, dict):
        exchange_map = {}

    binance_doc = load_json(BINANCE_MOVERS_PATH, {"items": []})
    external_doc = load_json(EXTERNAL_MOVERS_PATH, {"items": []})

    raw_items: List[Dict[str, Any]] = []
    raw_items.extend(binance_doc.get("items", []) if isinstance(binance_doc, dict) else [])
    raw_items.extend(external_doc.get("items", []) if isinstance(external_doc, dict) else [])

    merged: Dict[str, Dict[str, Any]] = {}

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        default_source = "external" if item.get("observation_only") else "market"
        normalized = normalize_item(item, default_source, exchange_map)
        if not normalized:
            continue

        symbol = normalized["symbol"]
        existing = merged.get(symbol)

        if existing is None:
            merged[symbol] = normalized
            continue

        # Préserver le meilleur signal absolu 24h, mais garder tradable=true si une source le permet.
        old_abs = abs(float(existing.get("chg_24h") or 0))
        new_abs = abs(float(normalized.get("chg_24h") or 0))
        if new_abs > old_abs:
            normalized["tradable"] = bool(normalized.get("tradable") or existing.get("tradable"))
            normalized["available_exchanges"] = sorted(set((normalized.get("available_exchanges") or []) + (existing.get("available_exchanges") or [])))
            merged[symbol] = normalized
        else:
            existing["tradable"] = bool(existing.get("tradable") or normalized.get("tradable"))
            existing["available_exchanges"] = sorted(set((existing.get("available_exchanges") or []) + (normalized.get("available_exchanges") or [])))

    items = list(merged.values())
    items.sort(key=lambda x: abs(float(x.get("chg_24h") or 0)), reverse=True)

    out = {
        "updated_at": utc_now(),
        "engine": "build_top_movers_combined_v1",
        "sources": {
            "market": str(BINANCE_MOVERS_PATH),
            "external": str(EXTERNAL_MOVERS_PATH),
            "exchange_map": str(TOKEN_EXCHANGE_MAP_PATH),
        },
        "summary": {
            "items_total": len(items),
            "tradable_count": sum(1 for x in items if x.get("tradable")),
            "observation_only_count": sum(1 for x in items if x.get("observation_only")),
        },
        "items": items,
    }

    save_json(OUT_PATH, out)
    print(json.dumps(out["summary"], indent=2, ensure_ascii=False))
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
