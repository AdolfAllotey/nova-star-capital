from __future__ import annotations

from typing import Dict


INSTRUMENTS: Dict[str, dict] = {
    "SHY": {
        "yahoo_symbol": "SHY",
        "currency": "USD",
    },
    "IEF": {
        "yahoo_symbol": "IEF",
        "currency": "USD",
    },
    "TLT": {
        "yahoo_symbol": "TLT",
        "currency": "USD",
    },
    "LQD": {
        "yahoo_symbol": "LQD",
        "currency": "USD",
    },
}


def get_instrument(symbol: str) -> dict:
    key = str(symbol or "").strip().upper()

    instrument = INSTRUMENTS.get(key)

    if instrument is None:
        raise KeyError(
            f"unknown bond instrument: {key!r}"
        )

    return {
        "symbol": key,
        **instrument,
    }


def get_currency(symbol: str) -> str:
    return str(
        get_instrument(symbol)["currency"]
    ).upper()


def get_yahoo_symbol(symbol: str) -> str:
    return str(
        get_instrument(symbol)["yahoo_symbol"]
    )
