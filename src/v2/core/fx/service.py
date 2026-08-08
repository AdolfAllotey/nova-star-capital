from __future__ import annotations

import os
from dataclasses import replace
from typing import Optional

from .cache import FXCache
from .models import FXConversion, FXRate
from .provider import FXProviderError, YahooFXProvider
from .validator import (
    normalize_currency,
    validate_rate,
)


class FXServiceError(RuntimeError):
    pass


class FXService:
    def __init__(
        self,
        provider: Optional[YahooFXProvider] = None,
        cache: Optional[FXCache] = None,
        fresh_cache_seconds: Optional[float] = None,
        fallback_cache_seconds: Optional[float] = None,
    ):
        self.provider = provider or YahooFXProvider()
        self.cache = cache or FXCache()

        self.fresh_cache_seconds = float(
            fresh_cache_seconds
            if fresh_cache_seconds is not None
            else os.getenv(
                "NSC_FX_FRESH_CACHE_SEC",
                "3600",
            )
        )

        self.fallback_cache_seconds = float(
            fallback_cache_seconds
            if fallback_cache_seconds is not None
            else os.getenv(
                "NSC_FX_FALLBACK_CACHE_SEC",
                "86400",
            )
        )

    def _identity_rate(
        self,
        currency: str,
    ) -> FXRate:
        return self.provider.fetch_rate(
            currency,
            currency,
        )

    def get_rate(
        self,
        base_currency: str,
        quote_currency: str,
        force_refresh: bool = False,
    ) -> FXRate:
        base = normalize_currency(base_currency)
        quote = normalize_currency(quote_currency)

        if base == quote:
            return self._identity_rate(base)

        if not force_refresh:
            fresh = self.cache.get(
                base,
                quote,
                self.fresh_cache_seconds,
            )

            if fresh is not None:
                return fresh

        direct_error = None

        try:
            direct = self.provider.fetch_rate(
                base,
                quote,
            )
            self.cache.put(direct)
            return direct

        except FXProviderError as exc:
            direct_error = exc

        try:
            inverse = self.provider.fetch_rate(
                quote,
                base,
            )

            converted = validate_rate(
                FXRate(
                    base_currency=base,
                    quote_currency=quote,
                    rate=1.0 / inverse.rate,
                    provider=inverse.provider,
                    market_timestamp=(
                        inverse.market_timestamp
                    ),
                    retrieved_at=inverse.retrieved_at,
                    is_cached=False,
                    cache_age_seconds=0.0,
                    inverted=True,
                )
            )

            self.cache.put(converted)
            return converted

        except Exception as inverse_error:
            fallback = self.cache.get(
                base,
                quote,
                self.fallback_cache_seconds,
            )

            if fallback is not None:
                return replace(
                    fallback,
                    is_cached=True,
                )

            raise FXServiceError(
                f"No valid FX rate available for "
                f"{base}/{quote}. "
                f"Direct error: {direct_error}. "
                f"Inverse error: {inverse_error}"
            ) from inverse_error

    def convert(
        self,
        amount: float,
        source_currency: str,
        target_currency: str,
        force_refresh: bool = False,
    ) -> FXConversion:
        try:
            numeric_amount = float(amount)
        except Exception as exc:
            raise FXServiceError(
                f"Invalid conversion amount: {amount!r}"
            ) from exc

        if numeric_amount < 0:
            raise FXServiceError(
                "Conversion amount cannot be negative"
            )

        source = normalize_currency(source_currency)
        target = normalize_currency(target_currency)

        rate = self.get_rate(
            source,
            target,
            force_refresh=force_refresh,
        )

        return FXConversion(
            source_amount=numeric_amount,
            source_currency=source,
            target_currency=target,
            rate=rate.rate,
            converted_amount=round(
                numeric_amount * rate.rate,
                8,
            ),
            rate_metadata=rate,
        )

    def refresh(
        self,
        base_currency: str,
        quote_currency: str,
    ) -> FXRate:
        return self.get_rate(
            base_currency,
            quote_currency,
            force_refresh=True,
        )

    def get_metadata(
        self,
        base_currency: str,
        quote_currency: str,
    ) -> dict:
        return self.get_rate(
            base_currency,
            quote_currency,
        ).to_dict()
