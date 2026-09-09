from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping


PROVIDER = "fred"
SERIES_ID = "DGS3MO"
UNIT = "percent_per_annum"
NORMALIZED_UNIT = "decimal_per_annum"
MAX_AGE_DAYS = 7
MIN_RATE_PERCENT = -5.0
MAX_RATE_PERCENT = 25.0


class OptionsRiskFreeRateError(RuntimeError):
    pass


@dataclass(frozen=True)
class CertifiedRiskFreeRateV3:
    provider: str
    series_id: str
    observation_date: str
    retrieved_at: str
    raw_rate_percent: float
    risk_free_rate: float
    source_unit: str
    normalized_unit: str
    age_days: int
    max_age_days: int
    freshness_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_utc_datetime(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise OptionsRiskFreeRateError(
                f"{field}: invalid datetime"
            ) from exc
    else:
        raise OptionsRiskFreeRateError(
            f"{field}: datetime required"
        )

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def _as_date(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise OptionsRiskFreeRateError(
                f"{field}: invalid date"
            ) from exc

    raise OptionsRiskFreeRateError(
        f"{field}: date required"
    )


def build_certified_risk_free_rate_v3(
    payload: Mapping[str, Any],
    *,
    retrieved_at: Any,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise OptionsRiskFreeRateError(
            "FRED payload must be a mapping"
        )

    observations = payload.get("observations")

    if not isinstance(observations, list) or not observations:
        raise OptionsRiskFreeRateError(
            "FRED payload has no observations"
        )

    retrieved_dt = _as_utc_datetime(
        retrieved_at,
        "retrieved_at",
    )

    usable: list[tuple[date, float]] = []

    for row in observations:
        if not isinstance(row, Mapping):
            continue

        raw_date = row.get("date")
        raw_value = row.get("value")

        if raw_value in {None, "", "."}:
            continue

        try:
            observation_date = _as_date(
                raw_date,
                "observation_date",
            )
            rate_percent = float(raw_value)
        except (TypeError, ValueError, OptionsRiskFreeRateError):
            continue

        if not math.isfinite(rate_percent):
            continue

        usable.append(
            (observation_date, rate_percent)
        )

    if not usable:
        raise OptionsRiskFreeRateError(
            "FRED payload has no usable observations"
        )

    usable.sort(key=lambda item: item[0])
    observation_date, rate_percent = usable[-1]

    if not (
        MIN_RATE_PERCENT
        <= rate_percent
        <= MAX_RATE_PERCENT
    ):
        raise OptionsRiskFreeRateError(
            "risk-free rate outside certified bounds"
        )

    age_days = (
        retrieved_dt.date() - observation_date
    ).days

    if age_days < 0:
        raise OptionsRiskFreeRateError(
            "risk-free observation is in the future"
        )

    if age_days > MAX_AGE_DAYS:
        raise OptionsRiskFreeRateError(
            "risk-free observation is stale"
        )

    normalized = rate_percent / 100.0

    return CertifiedRiskFreeRateV3(
        provider=PROVIDER,
        series_id=SERIES_ID,
        observation_date=observation_date.isoformat(),
        retrieved_at=(
            retrieved_dt.isoformat()
            .replace("+00:00", "Z")
        ),
        raw_rate_percent=rate_percent,
        risk_free_rate=normalized,
        source_unit=UNIT,
        normalized_unit=NORMALIZED_UNIT,
        age_days=age_days,
        max_age_days=MAX_AGE_DAYS,
        freshness_verified=True,
    ).to_dict()
