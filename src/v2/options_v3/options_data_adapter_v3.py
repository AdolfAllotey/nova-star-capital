from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Iterable


class OptionsDataAdapterError(ValueError):
    """Raised when mandatory Options V3 data cannot be normalized safely."""


@dataclass(frozen=True)
class AdaptedGreeksInputV3:
    underlying_price: float
    strike_price: float
    time_to_expiry_years: float
    volatility: float
    option_type: str
    valuation_timestamp: str
    volatility_source: str
    option_type_source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptedSizingInputV3:
    available_risk_eur: float
    max_trade_risk_eur: float
    premium_per_contract: float
    contract_multiplier: int
    maximum_loss_per_contract: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptedExpirationInputV3:
    expiration: str
    days_to_expiry: float
    valuation_timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptedAssignmentInputV3:
    option_type: str
    expiration: str
    days_to_expiry: float
    moneyness: float
    moneyness_source: str
    valuation_timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first_present(payload: dict[str, Any], keys: Iterable[str]) -> tuple[Any, str | None]:
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return value, key
    return None, None


def _finite_float(value: Any, field: str, *, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise OptionsDataAdapterError(f"{field}: invalid numeric value") from exc

    if not isfinite(number):
        raise OptionsDataAdapterError(f"{field}: non-finite numeric value")

    if minimum is not None and number < minimum:
        raise OptionsDataAdapterError(
            f"{field}: value {number} below minimum {minimum}"
        )

    return number


def _positive_float(value: Any, field: str) -> float:
    number = _finite_float(value, field)
    if number <= 0:
        raise OptionsDataAdapterError(f"{field}: value must be > 0")
    return number


def _utc_datetime(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise OptionsDataAdapterError(
                f"{field}: invalid datetime"
            ) from exc
    else:
        raise OptionsDataAdapterError(f"{field}: datetime required")

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result.astimezone(timezone.utc)


def _valuation_time(value: Any | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return _utc_datetime(value, "valuation_timestamp")


def _normalize_option_type(
    candidate: dict[str, Any],
) -> tuple[str, str]:
    value, source = _first_present(
        candidate,
        (
            "option_type",
            "right",
            "call_put",
            "put_call",
            "contract_type",
        ),
    )

    if value is not None:
        normalized = str(value).strip().upper()
        aliases = {
            "C": "CALL",
            "CALL": "CALL",
            "P": "PUT",
            "PUT": "PUT",
        }
        if normalized in aliases:
            return aliases[normalized], str(source)

    strategy = str(candidate.get("strategy", "")).strip().lower()
    put_markers = (
        "put",
        "cash_secured_put",
        "bull_put",
        "bear_put",
    )
    call_markers = (
        "call",
        "covered_call",
        "bull_call",
        "bear_call",
    )

    if any(marker in strategy for marker in put_markers):
        return "PUT", "derived_from_strategy"

    if any(marker in strategy for marker in call_markers):
        return "CALL", "derived_from_strategy"

    raise OptionsDataAdapterError("option_type: unable to normalize")


def _normalize_volatility(
    candidate: dict[str, Any],
) -> tuple[float, str]:
    value, source = _first_present(
        candidate,
        (
            "implied_volatility",
            "iv",
            "volatility",
            "historical_volatility",
            "annualized_volatility",
        ),
    )

    if value is None:
        raise OptionsDataAdapterError("volatility: no source available")

    volatility = _positive_float(value, "volatility")
    if volatility > 3.0:
        volatility /= 100.0

    if volatility > 3.0:
        raise OptionsDataAdapterError("volatility: implausible normalized value")

    return volatility, str(source)


def _normalize_expiration(
    candidate: dict[str, Any],
    valuation: datetime,
) -> tuple[datetime, float]:
    dte_value, _ = _first_present(
        candidate,
        ("days_to_expiry", "dte"),
    )

    expiration_value, _ = _first_present(
        candidate,
        (
            "expiration",
            "expiry",
            "expiration_date",
            "expiry_date",
        ),
    )

    if expiration_value is not None:
        expiration = _utc_datetime(expiration_value, "expiration")
        days_to_expiry = (
            expiration - valuation
        ).total_seconds() / 86400.0
    elif dte_value is not None:
        days_to_expiry = _finite_float(
            dte_value,
            "days_to_expiry",
            minimum=0.0,
        )
        expiration = valuation + __import__("datetime").timedelta(
            days=days_to_expiry
        )
    else:
        raise OptionsDataAdapterError(
            "expiration: neither expiration nor DTE available"
        )

    if days_to_expiry < 0:
        raise OptionsDataAdapterError("expiration: contract already expired")

    return expiration, days_to_expiry


def adapt_greeks_input_v3(
    candidate: dict[str, Any],
    *,
    valuation_timestamp: Any | None = None,
) -> AdaptedGreeksInputV3:
    valuation = _valuation_time(valuation_timestamp)

    underlying, _ = _first_present(
        candidate,
        (
            "underlying_price",
            "underlying_last",
            "underlying_mark",
            "spot_price",
            "stock_price",
            "market_price",
            "current_price",
            "last_price",
            "close",
        ),
    )
    strike, _ = _first_present(
        candidate,
        (
            "strike_price",
            "strike",
            "option_strike",
        ),
    )

    expiration, days_to_expiry = _normalize_expiration(
        candidate,
        valuation,
    )
    volatility, volatility_source = _normalize_volatility(candidate)
    option_type, option_type_source = _normalize_option_type(candidate)

    return AdaptedGreeksInputV3(
        underlying_price=_positive_float(
            underlying,
            "underlying_price",
        ),
        strike_price=_positive_float(
            strike,
            "strike_price",
        ),
        time_to_expiry_years=max(
            days_to_expiry / 365.0,
            1.0 / (365.0 * 24.0),
        ),
        volatility=volatility,
        option_type=option_type,
        valuation_timestamp=valuation.isoformat(),
        volatility_source=volatility_source,
        option_type_source=option_type_source,
    )


def adapt_sizing_input_v3(
    candidate: dict[str, Any],
    risk_context: dict[str, Any],
) -> AdaptedSizingInputV3:
    available, _ = _first_present(
        risk_context,
        (
            "available_risk_eur",
            "internal_available_risk_eur",
            "remaining_risk_eur",
            "risk_available_eur",
            "available_budget_eur",
        ),
    )

    if available is None:
        maximum, _ = _first_present(
            risk_context,
            (
                "max_total_risk_eur",
                "internal_max_total_risk_eur",
            ),
        )
        used, _ = _first_present(
            risk_context,
            (
                "used_risk_eur",
                "internal_used_risk_eur",
            ),
        )
        if maximum is not None and used is not None:
            available = max(
                0.0,
                _finite_float(maximum, "max_total_risk_eur")
                - _finite_float(used, "used_risk_eur"),
            )

    max_trade, _ = _first_present(
        risk_context,
        (
            "max_trade_risk_eur",
            "internal_max_trade_risk_eur",
            "risk_budget_eur",
            "trade_risk_limit_eur",
        ),
    )

    premium, _ = _first_present(
        candidate,
        (
            "premium_per_contract",
            "option_premium",
            "premium",
            "entry_price",
            "mark_price",
            "mid_price",
        ),
    )

    if premium is None:
        bid = candidate.get("bid")
        ask = candidate.get("ask")
        if bid is not None and ask is not None:
            premium = (
                _positive_float(bid, "bid")
                + _positive_float(ask, "ask")
            ) / 2.0

    multiplier = int(candidate.get("contract_multiplier", 100) or 100)
    if multiplier <= 0:
        raise OptionsDataAdapterError(
            "contract_multiplier: must be positive"
        )

    maximum_loss = candidate.get("maximum_loss_per_contract")

    if maximum_loss is not None:
        maximum_loss = _positive_float(
            maximum_loss,
            "maximum_loss_per_contract",
        )

    return AdaptedSizingInputV3(
        available_risk_eur=_finite_float(
            available,
            "available_risk_eur",
            minimum=0.0,
        ),
        max_trade_risk_eur=_positive_float(
            max_trade,
            "max_trade_risk_eur",
        ),
        premium_per_contract=_positive_float(
            premium,
            "premium_per_contract",
        ),
        contract_multiplier=multiplier,
        maximum_loss_per_contract=maximum_loss,
    )


def adapt_expiration_input_v3(
    candidate: dict[str, Any],
    *,
    valuation_timestamp: Any | None = None,
) -> AdaptedExpirationInputV3:
    valuation = _valuation_time(valuation_timestamp)
    expiration, days_to_expiry = _normalize_expiration(
        candidate,
        valuation,
    )

    return AdaptedExpirationInputV3(
        expiration=expiration.isoformat(),
        days_to_expiry=days_to_expiry,
        valuation_timestamp=valuation.isoformat(),
    )


def _derive_moneyness(
    position: dict[str, Any],
    option_type: str,
) -> tuple[float, str]:
    value, source = _first_present(
        position,
        (
            "moneyness",
            "moneyness_pct",
        ),
    )

    if value is not None:
        number = _finite_float(value, "moneyness")
        if abs(number) > 3.0:
            number /= 100.0
        return number, str(source)

    underlying, _ = _first_present(
        position,
        (
            "underlying_price",
            "current_price",
            "market_price",
            "last_price",
            "close",
        ),
    )
    strike, _ = _first_present(
        position,
        (
            "strike_price",
            "strike",
            "option_strike",
        ),
    )

    underlying_value = _positive_float(
        underlying,
        "underlying_price",
    )
    strike_value = _positive_float(
        strike,
        "strike_price",
    )

    if option_type == "CALL":
        result = (underlying_value - strike_value) / strike_value
    else:
        result = (strike_value - underlying_value) / strike_value

    return result, "derived_from_underlying_strike_option_type"


def adapt_assignment_input_v3(
    position: dict[str, Any],
    *,
    valuation_timestamp: Any | None = None,
) -> AdaptedAssignmentInputV3:
    valuation = _valuation_time(valuation_timestamp)
    option_type, _ = _normalize_option_type(position)
    expiration, days_to_expiry = _normalize_expiration(
        position,
        valuation,
    )
    moneyness, moneyness_source = _derive_moneyness(
        position,
        option_type,
    )

    return AdaptedAssignmentInputV3(
        option_type=option_type,
        expiration=expiration.isoformat(),
        days_to_expiry=days_to_expiry,
        moneyness=moneyness,
        moneyness_source=moneyness_source,
        valuation_timestamp=valuation.isoformat(),
    )
