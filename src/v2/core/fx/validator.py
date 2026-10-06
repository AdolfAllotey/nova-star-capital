from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Optional

from .market_clock import fx_open_seconds_between
from .models import FXRate


_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class FXValidationError(ValueError):
    pass


def normalize_currency(value: str) -> str:
    currency = str(value or "").strip().upper()

    if not _CURRENCY_RE.fullmatch(currency):
        raise FXValidationError(
            f"Invalid ISO-like currency code: {value!r}"
        )

    return currency


def parse_iso_timestamp(value: str) -> Optional[datetime]:
    try:
        raw = str(value or "").strip()

        if not raw:
            return None

        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"

        parsed = datetime.fromisoformat(raw)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except Exception:
        return None


def market_age_seconds(
    rate: FXRate,
    *,
    now: Optional[datetime] = None,
) -> float:
    market_ts = parse_iso_timestamp(
        rate.market_timestamp
    )

    if market_ts is None:
        raise FXValidationError(
            f"Invalid market timestamp for {rate.pair}"
        )

    reference = (
        now.astimezone(timezone.utc)
        if now is not None
        else datetime.now(timezone.utc)
    )

    wall_age = (
        reference - market_ts
    ).total_seconds()

    if wall_age < -300.0:
        raise FXValidationError(
            f"Future FX market timestamp for "
            f"{rate.pair}: age_seconds={wall_age}"
        )

    if wall_age <= 0.0:
        return 0.0

    return fx_open_seconds_between(
        market_ts,
        reference,
    )


def validate_market_freshness(
    rate: FXRate,
    *,
    max_market_age_seconds: float,
    now: Optional[datetime] = None,
) -> FXRate:
    validated = validate_rate(rate)

    try:
        maximum = float(max_market_age_seconds)
    except Exception as exc:
        raise FXValidationError(
            "Invalid FX market freshness limit"
        ) from exc

    if not math.isfinite(maximum) or maximum < 0:
        raise FXValidationError(
            "Invalid FX market freshness limit"
        )

    age = market_age_seconds(
        validated,
        now=now,
    )

    if age > maximum:
        raise FXValidationError(
            f"Stale FX market observation for "
            f"{validated.pair}: "
            f"market_age_seconds={age:.3f}, "
            f"max_market_age_seconds={maximum:.3f}"
        )

    return validated


def validate_rate(rate: FXRate) -> FXRate:
    normalize_currency(rate.base_currency)
    normalize_currency(rate.quote_currency)

    if rate.base_currency == rate.quote_currency:
        if rate.rate != 1.0:
            raise FXValidationError(
                "Identity currency rate must equal 1.0"
            )
        return rate

    if not math.isfinite(rate.rate) or rate.rate <= 0:
        raise FXValidationError(
            f"Invalid FX rate for {rate.pair}: {rate.rate}"
        )

    if not rate.provider:
        raise FXValidationError(
            f"Missing provider for {rate.pair}"
        )

    if parse_iso_timestamp(rate.market_timestamp) is None:
        raise FXValidationError(
            f"Invalid market timestamp for {rate.pair}"
        )

    if parse_iso_timestamp(rate.retrieved_at) is None:
        raise FXValidationError(
            f"Invalid retrieval timestamp for {rate.pair}"
        )

    return rate
