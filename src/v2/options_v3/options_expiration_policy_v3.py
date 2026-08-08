from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class ExpirationSelectionV3:
    selected_expiration: str | None
    days_to_expiry: int | None
    expiration_policy_valid: bool
    selection_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreExpiryDecisionV3:
    pre_expiry_close_required: bool
    days_to_expiry: int | None
    close_reason: str | None
    expiration_policy_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_utc_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(
            value,
            datetime.min.time(),
        )
    elif isinstance(value, str):
        normalized = value.strip().replace(
            "Z",
            "+00:00",
        )

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                parsed = datetime.strptime(
                    value.strip(),
                    "%Y-%m-%d",
                )
            except ValueError:
                return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def select_expiration_v3(
    *,
    expirations: Iterable[Any],
    current_timestamp: Any,
    minimum_days_to_expiry: int = 21,
    target_days_to_expiry: int = 30,
    maximum_days_to_expiry: int = 60,
) -> dict[str, Any]:
    now = _as_utc_datetime(current_timestamp)

    if now is None:
        return ExpirationSelectionV3(
            selected_expiration=None,
            days_to_expiry=None,
            expiration_policy_valid=False,
            selection_reason="invalid_current_timestamp",
        ).to_dict()

    minimum_dte = max(0, int(minimum_days_to_expiry))
    target_dte = max(minimum_dte, int(target_days_to_expiry))
    maximum_dte = max(target_dte, int(maximum_days_to_expiry))

    candidates: list[tuple[int, datetime]] = []

    for raw_expiration in expirations:
        expiration = _as_utc_datetime(raw_expiration)

        if expiration is None:
            continue

        days = (expiration.date() - now.date()).days

        if minimum_dte <= days <= maximum_dte:
            candidates.append((days, expiration))

    if not candidates:
        return ExpirationSelectionV3(
            selected_expiration=None,
            days_to_expiry=None,
            expiration_policy_valid=False,
            selection_reason="no_expiration_within_policy_window",
        ).to_dict()

    selected_days, selected_expiration = min(
        candidates,
        key=lambda row: (
            abs(row[0] - target_dte),
            row[0],
        ),
    )

    return ExpirationSelectionV3(
        selected_expiration=(
            selected_expiration.date().isoformat()
        ),
        days_to_expiry=selected_days,
        expiration_policy_valid=True,
        selection_reason="closest_expiration_to_target_dte",
    ).to_dict()


def evaluate_pre_expiry_close_v3(
    *,
    expiration: Any,
    current_timestamp: Any,
    position_status: str,
    pnl_pct: float | None = None,
    mandatory_close_days_before_expiry: int = 3,
    profit_take_pct: float | None = None,
    stop_loss_pct: float | None = None,
) -> dict[str, Any]:
    expiration_dt = _as_utc_datetime(expiration)
    current_dt = _as_utc_datetime(current_timestamp)

    if expiration_dt is None or current_dt is None:
        return PreExpiryDecisionV3(
            pre_expiry_close_required=True,
            days_to_expiry=None,
            close_reason="invalid_or_missing_expiration_data",
            expiration_policy_valid=False,
        ).to_dict()

    days_to_expiry = (
        expiration_dt.date() - current_dt.date()
    ).days

    normalized_status = str(position_status).strip().lower()

    if normalized_status in {
        "closed",
        "expired",
        "assigned",
        "exercised",
    }:
        return PreExpiryDecisionV3(
            pre_expiry_close_required=False,
            days_to_expiry=days_to_expiry,
            close_reason="position_already_terminal",
            expiration_policy_valid=True,
        ).to_dict()

    if days_to_expiry <= int(
        mandatory_close_days_before_expiry
    ):
        return PreExpiryDecisionV3(
            pre_expiry_close_required=True,
            days_to_expiry=days_to_expiry,
            close_reason="mandatory_pre_expiry_close",
            expiration_policy_valid=True,
        ).to_dict()

    try:
        pnl = (
            float(pnl_pct)
            if pnl_pct is not None
            else None
        )
    except (TypeError, ValueError):
        pnl = None

    if (
        pnl is not None
        and profit_take_pct is not None
        and pnl >= float(profit_take_pct)
    ):
        return PreExpiryDecisionV3(
            pre_expiry_close_required=True,
            days_to_expiry=days_to_expiry,
            close_reason="profit_take_threshold_reached",
            expiration_policy_valid=True,
        ).to_dict()

    if (
        pnl is not None
        and stop_loss_pct is not None
        and pnl <= float(stop_loss_pct)
    ):
        return PreExpiryDecisionV3(
            pre_expiry_close_required=True,
            days_to_expiry=days_to_expiry,
            close_reason="stop_loss_threshold_reached",
            expiration_policy_valid=True,
        ).to_dict()

    return PreExpiryDecisionV3(
        pre_expiry_close_required=False,
        days_to_expiry=days_to_expiry,
        close_reason=None,
        expiration_policy_valid=True,
    ).to_dict()
