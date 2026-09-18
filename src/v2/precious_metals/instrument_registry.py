from __future__ import annotations


INSTRUMENTS = {
    "GLD": {
        "yahoo_symbol": "GLD",
        "currency": "USD",
    },
    "SLV": {
        "yahoo_symbol": "SLV",
        "currency": "USD",
    },
}


def get_instrument(symbol: str) -> dict:
    key = str(symbol or "").strip().upper()

    try:
        return dict(INSTRUMENTS[key])
    except KeyError as exc:
        raise KeyError(
            f"unsupported precious-metals instrument: {key}"
        ) from exc
