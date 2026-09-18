from __future__ import annotations

from typing import Dict


INSTRUMENTS: Dict[str, dict] = {
    # US-listed securities — USD
    "PG": {
        "yahoo_symbol": "PG",
        "currency": "USD",
    },
    "KO": {
        "yahoo_symbol": "KO",
        "currency": "USD",
    },
    "PEP": {
        "yahoo_symbol": "PEP",
        "currency": "USD",
    },
    "WMT": {
        "yahoo_symbol": "WMT",
        "currency": "USD",
    },
    "COST": {
        "yahoo_symbol": "COST",
        "currency": "USD",
    },
    "CL": {
        "yahoo_symbol": "CL",
        "currency": "USD",
    },
    "MDLZ": {
        "yahoo_symbol": "MDLZ",
        "currency": "USD",
    },
    "JNJ": {
        "yahoo_symbol": "JNJ",
        "currency": "USD",
    },
    "UNH": {
        "yahoo_symbol": "UNH",
        "currency": "USD",
    },
    "ABT": {
        "yahoo_symbol": "ABT",
        "currency": "USD",
    },
    "MRK": {
        "yahoo_symbol": "MRK",
        "currency": "USD",
    },
    "PFE": {
        "yahoo_symbol": "PFE",
        "currency": "USD",
    },
    "LLY": {
        "yahoo_symbol": "LLY",
        "currency": "USD",
    },
    "NEE": {
        "yahoo_symbol": "NEE",
        "currency": "USD",
    },
    "DUK": {
        "yahoo_symbol": "DUK",
        "currency": "USD",
    },
    "SO": {
        "yahoo_symbol": "SO",
        "currency": "USD",
    },
    "UNP": {
        "yahoo_symbol": "UNP",
        "currency": "USD",
    },

    # Canadian National — NYSE listing used by current refresher.
    "CNI": {
        "yahoo_symbol": "CNI",
        "currency": "USD",
    },

    # European names.
    "MC": {
        "yahoo_symbol": "MC.PA",
        "currency": "EUR",
    },
    "AI": {
        "yahoo_symbol": "AI.PA",
        "currency": "EUR",
    },
    "NESN": {
        "yahoo_symbol": "NESN.SW",
        "currency": "CHF",
    },

    # Unilever ADR — NYSE listing.
    "UL": {
        "yahoo_symbol": "UL",
        "currency": "USD",
    },

    # Roche participation certificate on SIX.
    # NSC logical symbol remains ROG.
    "ROG": {
        "yahoo_symbol": "ROP.SW",
        "currency": "CHF",
    },

    # Novo Nordisk B share on Copenhagen.
    "NOVO-B": {
        "yahoo_symbol": "NOVO-B.CO",
        "currency": "DKK",
    },

    # ASML Nasdaq listing.
    "ASML": {
        "yahoo_symbol": "ASML",
        "currency": "USD",
    },

    # Defensive ETFs — US listings.
    "USMV": {
        "yahoo_symbol": "USMV",
        "currency": "USD",
    },
    "VIG": {
        "yahoo_symbol": "VIG",
        "currency": "USD",
    },
    "XLV": {
        "yahoo_symbol": "XLV",
        "currency": "USD",
    },
    "XLP": {
        "yahoo_symbol": "XLP",
        "currency": "USD",
    },
    "VDC": {
        "yahoo_symbol": "VDC",
        "currency": "USD",
    },
}


def get_instrument(symbol: str) -> dict:
    key = str(symbol or "").strip().upper()

    instrument = INSTRUMENTS.get(key)

    if instrument is None:
        raise KeyError(
            f"unknown defensive instrument: {key!r}"
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


def yahoo_symbols() -> list[str]:
    return [
        row["yahoo_symbol"]
        for row in INSTRUMENTS.values()
    ]


def yahoo_aliases() -> dict[str, str]:
    return {
        row["yahoo_symbol"]: symbol
        for symbol, row in INSTRUMENTS.items()
        if row["yahoo_symbol"] != symbol
    }
