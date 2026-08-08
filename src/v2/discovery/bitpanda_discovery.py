#!/usr/bin/env python3
"""
NSC — Bitpanda Discovery Collector V1.

Role
----
Collecte les actifs crypto proposés par le ticker Bitpanda, normalise
leur variation sur 24 heures et produit l'artefact attendu par :

    src/v2/discovery/market_discovery_engine.py

Sortie
------
<NSC_DATA_DIR>/market/bitpanda_top_movers.json

Bitpanda est ici une source de Discovery et de confirmation.
Ce module ne donne aucun droit d'exécution à Bitpanda et ne modifie
pas les règles de tradabilité de NSC.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SOURCE = "bitpanda"
ENGINE = "bitpanda_discovery_v1"

DEFAULT_API_URL = "https://developer.bitpanda.com/v1/ticker"
DEFAULT_PAGE_SIZE = 500
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_PAGES = 20
DEFAULT_RETRIES = 3

SUPPORTED_TYPES = {"cryptocoin"}
SUPPORTED_GROUPS = {
    "coin",
    "token",
    "leveraged_token",
    "security_token",
}

STABLECOINS = {
    "USDT",
    "USDC",
    "DAI",
    "FDUSD",
    "TUSD",
    "USDP",
    "EURT",
    "EURC",
    "PYUSD",
    "GUSD",
    "BUSD",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_data_dir() -> Path:
    raw = (
        os.getenv("NSC_DATA_DIR")
        or os.getenv("DATA_DIR")
        or "/opt/nsc/data/preprod"
    )
    return Path(raw).expanduser().resolve()


def get_output_path() -> Path:
    explicit = os.getenv("BITPANDA_DISCOVERY_OUTPUT")
    if explicit:
        return Path(explicit).expanduser().resolve()

    return get_data_dir() / "market" / "bitpanda_top_movers.json"


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip().replace(",", ".")

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if result != result:  # NaN
        return None

    if result in (float("inf"), float("-inf")):
        return None

    return result


def normalize_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def normalize_ticker_item(row: dict[str, Any]) -> dict[str, Any] | None:
    """
    Convertit une ligne du ticker Bitpanda vers le contrat NSC.

    Le contrat produit reste compatible avec discovery_utils.normalize_mover.
    """
    if not isinstance(row, dict):
        return None

    asset_type = str(row.get("type") or "").strip().lower()
    group = str(row.get("group") or "").strip().lower()

    if asset_type and asset_type not in SUPPORTED_TYPES:
        return None

    if group and group not in SUPPORTED_GROUPS:
        return None

    symbol = normalize_symbol(row.get("symbol"))
    if not symbol or symbol in STABLECOINS:
        return None

    price = safe_float(row.get("price"))
    change_24h = safe_float(row.get("price_change_day"))

    if price is None or price <= 0:
        return None

    if change_24h is None:
        return None

    currency = normalize_symbol(row.get("currency")) or "EUR"

    return {
        "id": str(row.get("id") or symbol),
        "symbol": symbol,
        "name": str(row.get("name") or symbol).strip(),
        "price": price,
        "currency": currency,
        "chg_1h": None,
        "chg_24h": change_24h,
        "chg_7d": None,
        "source": SOURCE,
        "pair": f"{symbol}EUR",
        "preferred_exchange": "bitpanda",
        "available_exchanges": ["bitpanda"],
        "asset_type": asset_type or "cryptocoin",
        "asset_group": group or None,
        "observation_only": True,
        "tradable_by_nsc": False,
    }


def build_query(cursor: str | None = None) -> str:
    params: dict[str, Any] = {
        "type": "cryptocoin",
        "group": "coin,token",
        "page_size": int(
            os.getenv("BITPANDA_PAGE_SIZE", str(DEFAULT_PAGE_SIZE))
        ),
    }

    if cursor:
        params["cursor"] = cursor

    return urlencode(params)


def fetch_page(
    api_key: str,
    cursor: str | None = None,
) -> dict[str, Any]:
    base_url = os.getenv("BITPANDA_TICKER_URL", DEFAULT_API_URL)
    timeout = int(
        os.getenv(
            "BITPANDA_TIMEOUT_SECONDS",
            str(DEFAULT_TIMEOUT_SECONDS),
        )
    )
    retries = int(
        os.getenv("BITPANDA_RETRIES", str(DEFAULT_RETRIES))
    )

    url = f"{base_url}?{build_query(cursor)}"

    request = Request(
        url=url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "Nova-Star-Capital/Bitpanda-Discovery-V1",
            "X-Api-Key": api_key,
        },
    )

    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
                doc = json.loads(payload)

                if not isinstance(doc, dict):
                    raise ValueError(
                        "Bitpanda returned a non-object JSON payload"
                    )

                return doc

        except HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass

            if exc.code in {401, 403}:
                raise RuntimeError(
                    "Bitpanda authentication rejected. "
                    "Check BITPANDA_API_KEY and its trading scope."
                ) from exc

            last_error = RuntimeError(
                f"Bitpanda HTTP {exc.code}: {body[:300]}"
            )

        except (URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(min(2 ** (attempt - 1), 5))

    raise RuntimeError(
        f"Bitpanda request failed after {retries} attempts: "
        f"{last_error!r}"
    )


def fetch_all_tickers(api_key: str) -> list[dict[str, Any]]:
    max_pages = int(
        os.getenv("BITPANDA_MAX_PAGES", str(DEFAULT_MAX_PAGES))
    )

    output: list[dict[str, Any]] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()

    for _page_number in range(1, max_pages + 1):
        payload = fetch_page(api_key=api_key, cursor=cursor)

        rows = payload.get("data")
        if not isinstance(rows, list):
            raise RuntimeError(
                "Bitpanda payload has no valid 'data' list"
            )

        output.extend(
            row for row in rows if isinstance(row, dict)
        )

        has_next_page = bool(payload.get("has_next_page"))
        next_cursor = payload.get("next_cursor")

        if not has_next_page:
            break

        if not next_cursor:
            raise RuntimeError(
                "Bitpanda announced another page without next_cursor"
            )

        cursor = str(next_cursor)

        if cursor in seen_cursors:
            raise RuntimeError(
                "Bitpanda pagination returned a repeated cursor"
            )

        seen_cursors.add(cursor)

    else:
        raise RuntimeError(
            f"Bitpanda pagination exceeded {max_pages} pages"
        )

    return output


def build_document(raw_rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_by_symbol: dict[str, dict[str, Any]] = {}

    rejected_count = 0

    for row in raw_rows:
        item = normalize_ticker_item(row)

        if item is None:
            rejected_count += 1
            continue

        symbol = item["symbol"]
        previous = normalized_by_symbol.get(symbol)

        if previous is None:
            normalized_by_symbol[symbol] = item
            continue

        previous_change = abs(
            safe_float(previous.get("chg_24h")) or 0.0
        )
        current_change = abs(
            safe_float(item.get("chg_24h")) or 0.0
        )

        if current_change > previous_change:
            normalized_by_symbol[symbol] = item

    items = list(normalized_by_symbol.values())

    # Les hausses et baisses les plus fortes remontent en premier.
    items.sort(
        key=lambda row: abs(float(row.get("chg_24h") or 0.0)),
        reverse=True,
    )

    gainers = [
        item for item in items
        if float(item.get("chg_24h") or 0.0) > 0
    ]
    losers = [
        item for item in items
        if float(item.get("chg_24h") or 0.0) < 0
    ]

    return {
        "status": "ok" if items else "empty",
        "engine": ENGINE,
        "version": "1.0.0",
        "generated_at": utc_now(),
        "source": SOURCE,
        "source_endpoint": "bitpanda_price_ticker",
        "mode": "observation_only",
        "currency": "mixed",
        "raw_count": len(raw_rows),
        "rejected_count": rejected_count,
        "count": len(items),
        "gainers_count": len(gainers),
        "losers_count": len(losers),
        "items": items,
        "top_gainers": gainers[:25],
        "top_losers": sorted(
            losers,
            key=lambda row: float(row.get("chg_24h") or 0.0),
        )[:25],
    }


def atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(f".{path.name}.tmp")

    temp_path.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(temp_path, path)


def run() -> dict[str, Any]:
    api_key = os.getenv("BITPANDA_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "BITPANDA_API_KEY is missing. "
            "Load /etc/nsc/bitpanda.env before running the collector."
        )

    raw_rows = fetch_all_tickers(api_key)
    document = build_document(raw_rows)

    output_path = get_output_path()
    atomic_write_json(output_path, document)

    return {
        "status": document["status"],
        "engine": ENGINE,
        "output": str(output_path),
        "raw_count": document["raw_count"],
        "count": document["count"],
        "gainers_count": document["gainers_count"],
        "losers_count": document["losers_count"],
        "top_symbols": [
            item["symbol"] for item in document["items"][:10]
        ],
    }


def main() -> int:
    try:
        result = run()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "engine": ENGINE,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
