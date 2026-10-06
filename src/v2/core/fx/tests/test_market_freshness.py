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


class FXMarketFreshnessTests(unittest.TestCase):

    def test_recent_open_market_observation_passes(self) -> None:
        rate = rate_at("2026-10-05T12:30:00Z")
        now = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

        self.assertIs(
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            ),
            rate,
        )

    def test_stale_open_market_observation_blocks(self) -> None:
        rate = rate_at("2026-10-05T11:00:00Z")
        now = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

        with self.assertRaises(FXValidationError):
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            )

    def test_weekend_does_not_consume_market_freshness(self) -> None:
        rate = rate_at("2026-10-02T21:29:05Z")
        now = datetime(2026, 10, 4, 18, 40, tzinfo=UTC)

        self.assertIs(
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            ),
            rate,
        )

    def test_old_friday_observation_still_blocks_on_weekend(self) -> None:
        rate = rate_at("2026-10-02T18:00:00Z")
        now = datetime(2026, 10, 4, 18, 40, tzinfo=UTC)

        with self.assertRaises(FXValidationError):
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            )

    def test_after_reopen_market_age_accumulates_again(self) -> None:
        rate = rate_at("2026-10-02T21:29:05Z")
        now = datetime(2026, 10, 4, 23, 30, tzinfo=UTC)

        with self.assertRaises(FXValidationError):
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            )

    def test_future_timestamp_still_blocks(self) -> None:
        rate = rate_at("2026-10-05T13:10:00Z")
        now = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)

        with self.assertRaises(FXValidationError):
            validate_market_freshness(
                rate,
                max_market_age_seconds=3600,
                now=now,
            )


if __name__ == "__main__":
    unittest.main()
