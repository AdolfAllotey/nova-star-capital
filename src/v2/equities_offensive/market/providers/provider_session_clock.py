#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Shared XNYS Session Clock

Single fail-closed temporal authority for provider-layer D1 data.

The implementation deliberately uses the exchange_calendars
session index and schedule directly. Some public parsing helpers in
exchange_calendars 4.11.3 combined with pandas 3.0.x can compare
nanosecond Timestamp values with microsecond-backed session values
and incorrectly report valid dates as out of bounds.
"""

from __future__ import annotations

from datetime import datetime, timezone

import exchange_calendars as xcals
import pandas as pd


def require_aware_datetime(
    value: datetime,
) -> datetime:
    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise RuntimeError(
            "xnys_reference_time_timezone_missing"
        )

    return value.astimezone(timezone.utc)


def latest_completed_xnys_session(
    reference_time: datetime,
) -> str:
    """
    Return the latest fully completed XNYS session at reference_time.

    reference_time is mandatory so callers cannot silently create
    independent wall-clock observations inside one provider run.
    """
    current = require_aware_datetime(
        reference_time
    )

    try:
        calendar = xcals.get_calendar("XNYS")
        sessions = calendar.sessions
        schedule = calendar.schedule
    except Exception as exc:
        raise RuntimeError(
            "xnys_calendar_unavailable"
        ) from exc

    if len(sessions) == 0:
        raise RuntimeError(
            "xnys_calendar_empty"
        )

    current_ts = pd.Timestamp(
        current
    ).tz_convert("UTC")

    current_date = (
        current_ts
        .tz_localize(None)
        .normalize()
    )

    first_session = sessions[0]
    last_session = sessions[-1]

    if current_date < first_session:
        raise RuntimeError(
            "xnys_reference_date_before_calendar"
        )

    if current_date > last_session:
        raise RuntimeError(
            "xnys_reference_date_after_calendar"
        )

    insertion = sessions.searchsorted(
        current_date,
        side="right",
    )

    if insertion <= 0:
        raise RuntimeError(
            "xnys_no_candidate_session"
        )

    candidate_index = insertion - 1
    candidate = sessions[candidate_index]

    try:
        close_ts = schedule.loc[
            candidate,
            "close",
        ]
    except Exception as exc:
        raise RuntimeError(
            "xnys_session_close_unavailable"
        ) from exc

    if pd.isna(close_ts):
        raise RuntimeError(
            "xnys_session_close_missing"
        )

    if current_ts < close_ts:
        candidate_index -= 1

        if candidate_index < 0:
            raise RuntimeError(
                "xnys_no_completed_session"
            )

        candidate = sessions[
            candidate_index
        ]

    return candidate.date().isoformat()
