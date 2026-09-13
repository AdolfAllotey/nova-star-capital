from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any


class OptionsPerformanceV3Error(ValueError):
    pass


def _parse_dt(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OptionsPerformanceV3Error(
            "options_v3_performance: timestamp required"
        )

    try:
        dt = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise OptionsPerformanceV3Error(
            "options_v3_performance: invalid timestamp"
        ) from exc

    if dt.tzinfo is None:
        raise OptionsPerformanceV3Error(
            "options_v3_performance: timezone required"
        )

    return dt.astimezone(timezone.utc)


def _finite_pnl(value: Any, *, field: str) -> float:
    try:
        pnl = float(value)
    except (TypeError, ValueError) as exc:
        raise OptionsPerformanceV3Error(
            f"options_v3_performance: {field} must be numeric"
        ) from exc

    if not isfinite(pnl):
        raise OptionsPerformanceV3Error(
            f"options_v3_performance: {field} must be finite"
        )

    return pnl


def build_options_performance_v3(
    *,
    open_positions: list[dict],
    closed_positions: list[dict],
    as_of: datetime,
) -> dict:
    if not isinstance(open_positions, list):
        raise OptionsPerformanceV3Error(
            "options_v3_performance: open_positions list required"
        )

    if not isinstance(closed_positions, list):
        raise OptionsPerformanceV3Error(
            "options_v3_performance: closed_positions list required"
        )

    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise OptionsPerformanceV3Error(
            "options_v3_performance: timezone-aware as_of required"
        )

    as_of_utc = as_of.astimezone(timezone.utc)
    today = as_of_utc.date()
    month_start = datetime(
        as_of_utc.year,
        as_of_utc.month,
        1,
        tzinfo=timezone.utc,
    )
    year_start = datetime(
        as_of_utc.year,
        1,
        1,
        tzinfo=timezone.utc,
    )

    realized_total = 0.0
    realized_daily = 0.0
    realized_mtd = 0.0
    realized_ytd = 0.0

    for position in closed_positions:
        if not isinstance(position, dict):
            raise OptionsPerformanceV3Error(
                "options_v3_performance: closed position dict required"
            )

        pnl = _finite_pnl(
            position.get("pnl_eur"),
            field="closed pnl_eur",
        )
        closed_at = _parse_dt(position.get("closed_at"))

        if closed_at > as_of_utc:
            raise OptionsPerformanceV3Error(
                "options_v3_performance: future closed_at"
            )

        realized_total += pnl

        if closed_at.date() == today:
            realized_daily += pnl
        if closed_at >= month_start:
            realized_mtd += pnl
        if closed_at >= year_start:
            realized_ytd += pnl

    unrealized_total = 0.0
    valued_open_count = 0
    unvalued_open_count = 0

    for position in open_positions:
        if not isinstance(position, dict):
            raise OptionsPerformanceV3Error(
                "options_v3_performance: open position dict required"
            )

        pnl_raw = position.get("pnl_eur")

        if pnl_raw is None:
            unvalued_open_count += 1
            continue

        unrealized_total += _finite_pnl(
            pnl_raw,
            field="open pnl_eur",
        )
        valued_open_count += 1

    valuation_status = (
        "COMPLETE"
        if unvalued_open_count == 0
        else "DEGRADED"
    )

    total_pnl = realized_total + unrealized_total

    return {
        "schema_version": 1,
        "as_of": as_of_utc.isoformat(),
        "currency": "EUR",
        "realized": {
            "total_pnl_eur": round(realized_total, 8),
            "daily_pnl_eur": round(realized_daily, 8),
            "mtd_pnl_eur": round(realized_mtd, 8),
            "ytd_pnl_eur": round(realized_ytd, 8),
        },
        "unrealized": {
            "current_pnl_eur": round(unrealized_total, 8),
            "valued_open_count": valued_open_count,
            "unvalued_open_count": unvalued_open_count,
            "valuation_status": valuation_status,
        },
        "total_pnl_eur": round(total_pnl, 8),
        "semantics": {
            "period_pnl_scope": "REALIZED_ONLY",
            "unrealized_scope": "CURRENT_SNAPSHOT",
            "daily_unrealized_delta_available": False,
        },
        "real_execution_allowed": False,
    }
