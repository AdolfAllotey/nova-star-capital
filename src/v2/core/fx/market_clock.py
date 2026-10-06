from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")

# Operational weekly FX boundary.
#
# The weekly close/reopen is expressed in New York local time so DST
# transitions are handled by zoneinfo rather than by fixed UTC hours.
_WEEKLY_BOUNDARY = time(17, 0)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError(
            "FX market clock requires timezone-aware datetime"
        )
    return value


def is_fx_market_open(value: datetime) -> bool:
    current = _aware(value).astimezone(NEW_YORK)
    weekday = current.weekday()
    clock = current.time().replace(tzinfo=None)

    if weekday <= 3:
        return True

    if weekday == 4:
        return clock < _WEEKLY_BOUNDARY

    if weekday == 5:
        return False

    return clock >= _WEEKLY_BOUNDARY


def _weekly_closed_interval(
    reference: datetime,
) -> tuple[datetime, datetime]:
    """
    Return the Friday 17:00 -> Sunday 17:00 New York closure
    associated with the local week containing reference.
    """
    local = _aware(reference).astimezone(NEW_YORK)

    monday = (
        local
        - timedelta(days=local.weekday())
    ).date()

    friday = monday + timedelta(days=4)
    sunday = monday + timedelta(days=6)

    close = datetime.combine(
        friday,
        _WEEKLY_BOUNDARY,
        tzinfo=NEW_YORK,
    ).astimezone(UTC)

    reopen = datetime.combine(
        sunday,
        _WEEKLY_BOUNDARY,
        tzinfo=NEW_YORK,
    ).astimezone(UTC)

    return close, reopen


def fx_open_seconds_between(
    start: datetime,
    end: datetime,
) -> float:
    """
    Return elapsed seconds during which the operational FX market
    was open between start and end.

    Weekly Friday 17:00 -> Sunday 17:00 New York closures consume
    zero freshness budget. DST is handled by America/New_York.
    """
    start_utc = _aware(start).astimezone(UTC)
    end_utc = _aware(end).astimezone(UTC)

    if end_utc <= start_utc:
        return 0.0

    elapsed = (end_utc - start_utc).total_seconds()

    start_local = start_utc.astimezone(NEW_YORK)
    end_local = end_utc.astimezone(NEW_YORK)

    first_monday = (
        start_local.date()
        - timedelta(days=start_local.weekday())
    )
    last_monday = (
        end_local.date()
        - timedelta(days=end_local.weekday())
    )

    monday = first_monday

    while monday <= last_monday:
        friday = monday + timedelta(days=4)
        sunday = monday + timedelta(days=6)

        closed_start = datetime.combine(
            friday,
            _WEEKLY_BOUNDARY,
            tzinfo=NEW_YORK,
        ).astimezone(UTC)

        closed_end = datetime.combine(
            sunday,
            _WEEKLY_BOUNDARY,
            tzinfo=NEW_YORK,
        ).astimezone(UTC)

        overlap_start = max(start_utc, closed_start)
        overlap_end = min(end_utc, closed_end)

        if overlap_end > overlap_start:
            elapsed -= (
                overlap_end - overlap_start
            ).total_seconds()

        monday += timedelta(days=7)

    return max(0.0, elapsed)
