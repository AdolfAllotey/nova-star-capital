from __future__ import annotations

from datetime import datetime, timezone
import unittest

from src.v2.core.fx.market_clock import (
    fx_open_seconds_between,
    is_fx_market_open,
)


UTC = timezone.utc


def dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(
        2026,
        10,
        day,
        hour,
        minute,
        tzinfo=UTC,
    )


class FXMarketClockTests(unittest.TestCase):

    def test_weekday_is_open(self) -> None:
        self.assertTrue(is_fx_market_open(dt(5, 13)))

    def test_friday_before_close_is_open(self) -> None:
        self.assertTrue(is_fx_market_open(dt(2, 20, 59)))

    def test_friday_at_close_is_closed(self) -> None:
        self.assertFalse(is_fx_market_open(dt(2, 22)))

    def test_saturday_is_closed(self) -> None:
        self.assertFalse(is_fx_market_open(dt(3, 12)))

    def test_sunday_before_reopen_is_closed(self) -> None:
        self.assertFalse(is_fx_market_open(dt(4, 18, 40)))

    def test_sunday_at_reopen_is_open(self) -> None:
        self.assertTrue(is_fx_market_open(dt(4, 22)))

    def test_weekend_consumes_only_remaining_friday_open_time(self) -> None:
        elapsed = fx_open_seconds_between(
            dt(2, 21, 29),
            dt(4, 18, 40),
        )
        self.assertEqual(elapsed, 0.0)

    def test_old_friday_quote_consumes_open_time(self) -> None:
        elapsed = fx_open_seconds_between(
            dt(2, 18),
            dt(4, 18, 40),
        )
        self.assertEqual(elapsed, 3 * 3600)

    def test_post_reopen_time_accumulates(self) -> None:
        elapsed = fx_open_seconds_between(
            dt(2, 21, 29),
            dt(4, 23, 30),
        )
        self.assertEqual(
            elapsed,
            150 * 60,
        )

    def test_normal_weekday_elapsed_time(self) -> None:
        elapsed = fx_open_seconds_between(
            dt(5, 12, 30),
            dt(5, 13),
        )
        self.assertEqual(elapsed, 30 * 60)


if __name__ == "__main__":
    unittest.main()


class FXMarketClockDSTTests(unittest.TestCase):

    def test_october_boundary_is_2100_utc(self) -> None:
        self.assertFalse(
            is_fx_market_open(
                datetime(
                    2026, 10, 2, 21, 0,
                    tzinfo=UTC,
                )
            )
        )
        self.assertTrue(
            is_fx_market_open(
                datetime(
                    2026, 10, 4, 21, 0,
                    tzinfo=UTC,
                )
            )
        )

    def test_december_boundary_is_2200_utc(self) -> None:
        self.assertTrue(
            is_fx_market_open(
                datetime(
                    2026, 12, 4, 21, 59, 59,
                    tzinfo=UTC,
                )
            )
        )
        self.assertFalse(
            is_fx_market_open(
                datetime(
                    2026, 12, 4, 22, 0,
                    tzinfo=UTC,
                )
            )
        )

    def test_real_yahoo_post_close_observation_has_zero_weekend_age(
        self,
    ) -> None:
        elapsed = fx_open_seconds_between(
            datetime(
                2026, 10, 2, 21, 29, 5,
                tzinfo=UTC,
            ),
            datetime(
                2026, 10, 4, 18, 40,
                tzinfo=UTC,
            ),
        )
        self.assertEqual(elapsed, 0.0)
