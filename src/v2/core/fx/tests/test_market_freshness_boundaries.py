from __future__ import annotations

from datetime import datetime, timezone
import unittest

from src.v2.core.fx.models import FXRate
from src.v2.core.fx.validator import (
    FXValidationError,
    validate_market_freshness,
)


UTC = timezone.utc


def rate_at(timestamp: str) -> FXRate:
    return FXRate(
        base_currency="EUR",
        quote_currency="USD",
        rate=1.17,
        provider="test",
        market_timestamp=timestamp,
        retrieved_at=timestamp,
    )


class FXFreshnessBoundaryTests(unittest.TestCase):

    def test_exactly_3600_open_seconds_passes(self) -> None:
        rate = rate_at("2026-10-05T12:00:00Z")
        now = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

        self.assertIs(
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            ),
            rate,
        )

    def test_3601_open_seconds_blocks(self) -> None:
        rate = rate_at("2026-10-05T11:59:59Z")
        now = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

        with self.assertRaises(FXValidationError):
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            )

    def test_exactly_300_seconds_future_is_tolerated(self) -> None:
        rate = rate_at("2026-10-05T13:05:00Z")
        now = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

        self.assertIs(
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            ),
            rate,
        )

    def test_301_seconds_future_blocks(self) -> None:
        rate = rate_at("2026-10-05T13:05:01Z")
        now = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

        with self.assertRaises(FXValidationError):
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            )

    def test_closed_weekend_consumes_zero_additional_seconds(self) -> None:
        rate = rate_at("2026-10-02T21:30:00Z")
        now = datetime(2026, 10, 4, 20, 59, 59, tzinfo=UTC)

        self.assertIs(
            validate_market_freshness(
                rate,
                max_market_age_seconds=1800,
                now=now,
            ),
            rate,
        )

    def test_one_second_after_reopen_exceeds_exact_budget(self) -> None:
        rate = rate_at("2026-10-02T20:30:00Z")
        now = datetime(2026, 10, 4, 21, 0, 1, tzinfo=UTC)

        with self.assertRaises(FXValidationError):
            validate_market_freshness(
                rate,
                max_market_age_seconds=1800,
                now=now,
            )


if __name__ == "__main__":
    unittest.main()
