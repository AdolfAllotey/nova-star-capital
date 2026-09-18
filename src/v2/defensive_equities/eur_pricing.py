from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.v2.core.fx import FXService
from src.v2.defensive_equities.instrument_registry import (
    get_instrument,
)


@dataclass(frozen=True)
class DefensiveEURPrice:
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
) -> Dict[str, DefensiveEURPrice]:
    if not isinstance(native_prices, dict):
        raise RuntimeError(
            "defensive native prices must be a dict"
        )

    service = fx_service or FXService()

    currencies: set[str] = set()
    normalized_native: Dict[str, float] = {}

    for raw_symbol, raw_price in native_prices.items():
        symbol = str(raw_symbol or "").strip().upper()

        if not symbol:
            raise RuntimeError(
                "defensive native price has empty symbol"
            )

        instrument = get_instrument(symbol)

        try:
            native_price = float(raw_price)
        except Exception as exc:
            raise RuntimeError(
                f"invalid native price for {symbol}: "
                f"{raw_price!r}"
            ) from exc

        if native_price <= 0:
            raise RuntimeError(
                f"non-positive native price for {symbol}: "
                f"{native_price}"
            )

        normalized_native[symbol] = native_price
        currencies.add(
            str(instrument["currency"]).upper()
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
                f"defensive FX unavailable for "
                f"{currency}/EUR: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        fx_value = float(rate.rate)

        if fx_value <= 0:
            raise RuntimeError(
                f"invalid defensive FX rate "
                f"{currency}/EUR={fx_value}"
            )

        rates[currency] = rate

    result: Dict[str, DefensiveEURPrice] = {}

    for symbol, native_price in normalized_native.items():
        instrument = get_instrument(symbol)
        currency = str(
            instrument["currency"]
        ).upper()

        rate = rates[currency]
        fx_value = float(rate.rate)
        price_eur = native_price * fx_value

        if price_eur <= 0:
            raise RuntimeError(
                f"invalid EUR price for {symbol}"
            )

        result[symbol] = DefensiveEURPrice(
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
