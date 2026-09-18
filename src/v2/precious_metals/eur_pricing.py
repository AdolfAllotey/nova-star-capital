from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.v2.core.fx import FXService
from src.v2.precious_metals.instrument_registry import (
    get_instrument,
)


@dataclass(frozen=True)
class MetalEURPrice:
    symbol: str
    yahoo_symbol: str
    native_currency: str
    native_price: float
    fx_to_eur: float
    price_eur: float
    fx: Dict[str, Any]


def _rate_metadata(rate: Any) -> Dict[str, Any]:
    return {
        "pair": getattr(rate, "pair", None),
        "rate": float(getattr(rate, "rate")),
        "provider": getattr(rate, "provider", None),
        "market_timestamp": getattr(
            rate,
            "market_timestamp",
            None,
        ),
        "retrieved_at": getattr(
            rate,
            "retrieved_at",
            None,
        ),
        "is_cached": bool(
            getattr(rate, "is_cached", False)
        ),
        "cache_age_seconds": getattr(
            rate,
            "cache_age_seconds",
            None,
        ),
        "inverted": bool(
            getattr(rate, "inverted", False)
        ),
    }


def build_eur_prices(
    native_prices: Dict[str, float],
    *,
    fx_service: Optional[Any] = None,
) -> Dict[str, MetalEURPrice]:
    if not isinstance(native_prices, dict):
        raise RuntimeError(
            "metals native prices must be a dict"
        )

    service = fx_service or FXService()

    normalized: Dict[str, float] = {}
    currencies: set[str] = set()

    for raw_symbol, raw_price in native_prices.items():
        symbol = str(
            raw_symbol or ""
        ).strip().upper()

        instrument = get_instrument(symbol)

        try:
            native_price = float(raw_price)
        except Exception as exc:
            raise RuntimeError(
                f"invalid metals native price "
                f"for {symbol}: {raw_price!r}"
            ) from exc

        if native_price <= 0:
            raise RuntimeError(
                f"non-positive metals native price "
                f"for {symbol}: {native_price}"
            )

        normalized[symbol] = native_price

        currencies.add(
            str(
                instrument["currency"]
            ).upper()
        )

    rates: Dict[str, Any] = {}

    for currency in sorted(currencies):
        try:
            rate = service.get_rate(
                currency,
                "EUR",
            )
        except Exception as exc:
            raise RuntimeError(
                f"metals FX unavailable for "
                f"{currency}/EUR: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        fx_value = float(rate.rate)

        if fx_value <= 0:
            raise RuntimeError(
                f"invalid metals FX rate "
                f"{currency}/EUR={fx_value}"
            )

        rates[currency] = rate

    result: Dict[str, MetalEURPrice] = {}

    for symbol, native_price in normalized.items():
        instrument = get_instrument(symbol)

        currency = str(
            instrument["currency"]
        ).upper()

        rate = rates[currency]
        fx_value = float(rate.rate)

        price_eur = (
            native_price
            * fx_value
        )

        result[symbol] = MetalEURPrice(
            symbol=symbol,
            yahoo_symbol=str(
                instrument["yahoo_symbol"]
            ),
            native_currency=currency,
            native_price=round(
                native_price,
                8,
            ),
            fx_to_eur=round(
                fx_value,
                12,
            ),
            price_eur=round(
                price_eur,
                8,
            ),
            fx=_rate_metadata(rate),
        )

    return result
