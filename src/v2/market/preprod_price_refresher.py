from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf


MAPS = {
    "/opt/nsc/data/preprod/defensive/prices.json": [
        "PG", "KO", "PEP", "WMT", "COST", "CL", "MDLZ", "JNJ",
        "UNH", "ABT", "MRK", "PFE", "LLY", "NEE", "DUK", "SO",
        "UNP", "CNI", "MC.PA", "AI.PA", "NESN.SW", "UL", "ROP.SW",
        "NOVO-B.CO", "ASML", "USMV", "VIG", "XLV", "XLP", "VDC",
    ],
    "/opt/nsc/data/preprod/bonds/prices.json": [
        "SHY", "IEF", "TLT", "LQD",
    ],
    "/opt/nsc/data/preprod/metals/prices.json": [
        "GLD", "SLV",
    ],
}

ALIASES = {
    "MC.PA": "MC",
    "AI.PA": "AI",
    "NESN.SW": "NESN",
    "ROP.SW": "ROG",
    "NOVO-B.CO": "NOVO-B",
}


def atomic_write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )

    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                indent=2,
                ensure_ascii=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def fetch_last(symbol: str):
    try:
        data = yf.Ticker(symbol).history(period="5d")

        if data is None or data.empty:
            return None

        close = data["Close"].dropna()
        if close.empty:
            return None

        price = float(close.iloc[-1])

        if price <= 0:
            return None

        return price

    except Exception:
        return None


def main() -> None:
    snapshots = {}
    failures = {}

    # Fetch everything before publishing anything.
    for out, symbols in MAPS.items():
        prices = {}
        missing = []

        for symbol in symbols:
            price = fetch_last(symbol)

            if price is None:
                missing.append(symbol)
                continue

            prices[ALIASES.get(symbol, symbol)] = round(
                price,
                4,
            )

        snapshots[out] = prices

        if missing:
            failures[out] = missing

    # Global fail-closed:
    # no sleeve is published if any expected price is missing.
    if failures:
        for out, missing in failures.items():
            print(
                f"DATA_SOURCE_FAILURE "
                f"path={out} "
                f"missing={','.join(missing)}"
            )

        raise RuntimeError(
            "shared price refresh incomplete; "
            "no artifacts published"
        )

    updated_at = datetime.now(timezone.utc).isoformat()

    for out, symbols in MAPS.items():
        path = Path(out)
        prices = snapshots[out]

        meta = {
            "status": "ok",
            "engine": "preprod_price_refresher_yfinance_v2",
            "updated_at": updated_at,
            "expected_count": len(symbols),
            "prices_count": len(prices),
            "coverage_pct": 100.0,
            "prices": prices,
        }

        # Publish prices first, metadata last.
        # If publication is interrupted, consumers keep seeing
        # stale metadata and therefore fail closed.
        atomic_write_json(path, prices)
        atomic_write_json(
            path.with_name("prices_meta.json"),
            meta,
        )

        print(
            f"REFRESH_OK "
            f"path={out} "
            f"count={len(prices)}"
        )


if __name__ == "__main__":
    main()
