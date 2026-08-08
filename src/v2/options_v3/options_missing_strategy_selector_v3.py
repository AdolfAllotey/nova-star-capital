from __future__ import annotations

from typing import Any
import math


EXTENDED_STRATEGIES = {
    "long_call",
    "bull_put_spread",
}

CONTRACT_MULTIPLIER = 100


class MissingStrategySelectionError(ValueError):
    """Fail-closed error for Options V3 strategy selection."""


def _finite_float(
    value: Any,
    field: str,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise MissingStrategySelectionError(
            f"invalid_{field}"
        ) from exc

    if not math.isfinite(result):
        raise MissingStrategySelectionError(
            f"invalid_{field}"
        )

    return result


def _positive_float(
    value: Any,
    field: str,
) -> float:
    result = _finite_float(
        value,
        field,
    )

    if result <= 0:
        raise MissingStrategySelectionError(
            f"non_positive_{field}"
        )

    return result


def _optional_non_negative_float(
    value: Any,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(result) or result < 0:
        return 0.0

    return result


def _normalized_text(
    value: Any,
) -> str:
    return str(
        value or ""
    ).strip()


def _normalized_upper(
    value: Any,
) -> str:
    return _normalized_text(
        value
    ).upper()


def _contract_expiration(
    contract: dict[str, Any],
) -> str:
    expiration = _normalized_text(
        contract.get("expiration")
        or contract.get("expiry")
    )

    if not expiration:
        raise MissingStrategySelectionError(
            "missing_expiration"
        )

    return expiration


def _contract_option_type(
    contract: dict[str, Any],
) -> str:
    option_type = _normalized_upper(
        contract.get("option_type")
        or contract.get("type")
    )

    if option_type not in {
        "CALL",
        "PUT",
    }:
        raise MissingStrategySelectionError(
            "invalid_option_type"
        )

    return option_type


def _contract_mid(
    contract: dict[str, Any],
) -> float:
    raw_mid = contract.get("mid")

    if raw_mid is not None:
        return _positive_float(
            raw_mid,
            "mid",
        )

    bid = _positive_float(
        contract.get("bid"),
        "bid",
    )

    ask = _positive_float(
        contract.get("ask"),
        "ask",
    )

    if ask < bid:
        raise MissingStrategySelectionError(
            "ask_below_bid"
        )

    return _positive_float(
        (bid + ask) / 2.0,
        "mid",
    )


def _validate_contract(
    contract: Any,
) -> dict[str, Any]:
    if not isinstance(
        contract,
        dict,
    ):
        raise MissingStrategySelectionError(
            "contract_not_dictionary"
        )

    normalized = dict(contract)

    contract_symbol = _normalized_text(
        normalized.get("contract_symbol")
        or normalized.get("contractSymbol")
    )

    if not contract_symbol:
        raise MissingStrategySelectionError(
            "missing_contract_symbol"
        )

    strike = _positive_float(
        normalized.get("strike"),
        "strike",
    )

    bid = _positive_float(
        normalized.get("bid"),
        "bid",
    )

    ask = _positive_float(
        normalized.get("ask"),
        "ask",
    )

    if ask < bid:
        raise MissingStrategySelectionError(
            "ask_below_bid"
        )

    implied_volatility = _positive_float(
        normalized.get("implied_volatility")
        or normalized.get("impliedVolatility"),
        "implied_volatility",
    )

    expiration = _contract_expiration(
        normalized
    )

    option_type = _contract_option_type(
        normalized
    )

    mid = _contract_mid(
        normalized
    )

    normalized.update({
        "contract_symbol": contract_symbol,
        "strike": strike,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "implied_volatility": implied_volatility,
        "expiration": expiration,
        "option_type": option_type,
        "open_interest": _optional_non_negative_float(
            normalized.get("open_interest")
            or normalized.get("openInterest")
        ),
        "volume": _optional_non_negative_float(
            normalized.get("volume")
        ),
    })

    return normalized


def _provider_metadata(
    provider_payload: dict[str, Any],
) -> dict[str, Any]:
    metadata = provider_payload.get(
        "metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        metadata = {}

    return metadata


def _provider_name(
    provider_payload: dict[str, Any],
) -> str:
    metadata = _provider_metadata(
        provider_payload
    )

    return _normalized_text(
        provider_payload.get("provider")
        or metadata.get("provider")
        or "yfinance"
    )


def _provider_timestamp(
    provider_payload: dict[str, Any],
) -> str:
    metadata = _provider_metadata(
        provider_payload
    )

    timestamp = _normalized_text(
        provider_payload.get(
            "provider_timestamp"
        )
        or provider_payload.get(
            "timestamp"
        )
        or metadata.get(
            "provider_timestamp"
        )
        or metadata.get(
            "fetched_at"
        )
        or metadata.get(
            "retrieval_timestamp"
        )
        or metadata.get(
            "timestamp"
        )
    )

    if not timestamp:
        raise MissingStrategySelectionError(
            "missing_provider_timestamp"
        )

    return timestamp


def _underlying_price(
    provider_payload: dict[str, Any],
) -> float:
    metadata = _provider_metadata(
        provider_payload
    )

    return _positive_float(
        provider_payload.get(
            "underlying_price"
        )
        or provider_payload.get(
            "spot"
        )
        or metadata.get(
            "underlying_price"
        )
        or metadata.get(
            "spot"
        ),
        "underlying_price",
    )


def _days_to_expiry(
    provider_payload: dict[str, Any],
    contracts: list[dict[str, Any]],
) -> float:
    metadata = _provider_metadata(
        provider_payload
    )

    candidates = [
        provider_payload.get(
            "days_to_expiry"
        ),
        provider_payload.get(
            "dte"
        ),
        metadata.get(
            "days_to_expiry"
        ),
        metadata.get(
            "dte"
        ),
    ]

    for contract in contracts:
        candidates.extend([
            contract.get(
                "days_to_expiry"
            ),
            contract.get(
                "dte"
            ),
        ])

    for value in candidates:
        try:
            result = float(value)
        except (TypeError, ValueError):
            continue

        if (
            math.isfinite(result)
            and result > 0
        ):
            return result

    raise MissingStrategySelectionError(
        "missing_days_to_expiry"
    )


def _eligible_contracts(
    provider_payload: dict[str, Any],
    option_type: str,
) -> list[dict[str, Any]]:
    if not isinstance(
        provider_payload,
        dict,
    ):
        raise MissingStrategySelectionError(
            "provider_payload_not_dictionary"
        )

    contracts = provider_payload.get(
        "contracts"
    )

    if not isinstance(
        contracts,
        list,
    ) or not contracts:
        raise MissingStrategySelectionError(
            "empty_option_chain"
        )

    eligible: list[dict[str, Any]] = []

    for raw_contract in contracts:
        try:
            contract = _validate_contract(
                raw_contract
            )
        except MissingStrategySelectionError:
            continue

        if (
            contract["option_type"]
            == option_type
        ):
            eligible.append(
                contract
            )

    if not eligible:
        raise MissingStrategySelectionError(
            f"no_eligible_{option_type.lower()}s"
        )

    return eligible


def _relative_spread(
    contract: dict[str, Any],
) -> float:
    mid = _positive_float(
        contract.get("mid"),
        "mid",
    )

    bid = _positive_float(
        contract.get("bid"),
        "bid",
    )

    ask = _positive_float(
        contract.get("ask"),
        "ask",
    )

    return max(
        ask - bid,
        0.0,
    ) / mid


def _leg_payload(
    contract: dict[str, Any],
    side: str,
) -> dict[str, Any]:
    return {
        "side": side,
        "option_type": contract[
            "option_type"
        ],
        "contract_symbol": contract[
            "contract_symbol"
        ],
        "expiration": contract[
            "expiration"
        ],
        "strike": contract[
            "strike"
        ],
        "bid": contract[
            "bid"
        ],
        "ask": contract[
            "ask"
        ],
        "mid": contract[
            "mid"
        ],
        "implied_volatility": contract[
            "implied_volatility"
        ],
        "open_interest": contract.get(
            "open_interest",
            0.0,
        ),
        "volume": contract.get(
            "volume",
            0.0,
        ),
        "contract_multiplier": (
            CONTRACT_MULTIPLIER
        ),
    }


def _base_result(
    *,
    strategy: str,
    provider_payload: dict[str, Any],
    expiration: str,
    days_to_expiry: float,
    contract_legs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "strategy": strategy,
        "selection_status": "SELECTED",
        "selector_engine": (
            "options_contract_selector_v3"
        ),
        "selector_version": (
            "extended_strategy_v1"
        ),
        "provider": _provider_name(
            provider_payload
        ),
        "provider_timestamp": (
            _provider_timestamp(
                provider_payload
            )
        ),
        "expiration": expiration,
        "days_to_expiry": (
            days_to_expiry
        ),
        "underlying_price": (
            _underlying_price(
                provider_payload
            )
        ),
        "contract_legs": contract_legs,
        "leg_count": len(
            contract_legs
        ),
        "contract_multiplier": (
            CONTRACT_MULTIPLIER
        ),
        "simulation_only": True,
        "real_execution_allowed": False,
    }


def select_long_call_v3(
    provider_payload: dict[str, Any],
) -> dict[str, Any]:
    underlying = _underlying_price(
        provider_payload
    )

    calls = _eligible_contracts(
        provider_payload,
        "CALL",
    )

    eligible = [
        contract
        for contract in calls
        if (
            underlying * 0.98
            <= contract["strike"]
            <= underlying * 1.05
        )
    ]

    if not eligible:
        raise MissingStrategySelectionError(
            "no_atm_or_slightly_otm_call"
        )

    def rank(
        contract: dict[str, Any],
    ) -> tuple[Any, ...]:
        strike = contract["strike"]

        return (
            abs(
                strike - underlying
            ),
            0 if strike >= underlying else 1,
            -contract.get(
                "open_interest",
                0.0,
            ),
            -contract.get(
                "volume",
                0.0,
            ),
            _relative_spread(
                contract
            ),
            strike,
        )

    selected = sorted(
        eligible,
        key=rank,
    )[0]

    debit = _positive_float(
        selected["mid"],
        "long_call_debit",
    )

    expiration = selected[
        "expiration"
    ]

    days_to_expiry = _days_to_expiry(
        provider_payload,
        [selected],
    )

    result = _base_result(
        strategy="long_call",
        provider_payload=provider_payload,
        expiration=expiration,
        days_to_expiry=days_to_expiry,
        contract_legs=[
            _leg_payload(
                selected,
                "BUY",
            )
        ],
    )

    result.update({
        "net_premium_per_share": (
            -debit
        ),
        "gross_debit_per_share": (
            debit
        ),
        "gross_credit_per_share": (
            0.0
        ),
        "spread_width": None,
        "maximum_loss_per_contract": (
            round(
                debit
                * CONTRACT_MULTIPLIER,
                6,
            )
        ),
        "maximum_profit_per_contract": (
            None
        ),
        "maximum_profit_profile": (
            "THEORETICALLY_UNLIMITED"
        ),
        "assignment_notional_per_contract": (
            None
        ),
    })

    return result


def select_bull_put_spread_v3(
    provider_payload: dict[str, Any],
) -> dict[str, Any]:
    underlying = _underlying_price(
        provider_payload
    )

    puts = _eligible_contracts(
        provider_payload,
        "PUT",
    )

    otm_puts = [
        contract
        for contract in puts
        if contract["strike"] < underlying
    ]

    if len(otm_puts) < 2:
        raise MissingStrategySelectionError(
            "insufficient_otm_puts"
        )

    candidates: list[
        tuple[
            tuple[Any, ...],
            dict[str, Any],
            dict[str, Any],
            float,
            float,
            float,
        ]
    ] = []

    expirations = sorted({
        contract["expiration"]
        for contract in otm_puts
    })

    for expiration in expirations:
        same_expiration = sorted(
            [
                contract
                for contract in otm_puts
                if (
                    contract["expiration"]
                    == expiration
                )
            ],
            key=lambda item: item["strike"],
            reverse=True,
        )

        for short_put in same_expiration:
            for long_put in same_expiration:
                if (
                    long_put["strike"]
                    >= short_put["strike"]
                ):
                    continue

                width = (
                    short_put["strike"]
                    - long_put["strike"]
                )

                if (
                    width < 1.0
                    or width > 20.0
                ):
                    continue

                credit = (
                    short_put["mid"]
                    - long_put["mid"]
                )

                if (
                    not math.isfinite(
                        credit
                    )
                    or credit <= 0
                    or credit >= width
                ):
                    continue

                maximum_profit = (
                    credit
                    * CONTRACT_MULTIPLIER
                )

                maximum_loss = (
                    width - credit
                ) * CONTRACT_MULTIPLIER

                if maximum_loss <= 0:
                    continue

                combined_open_interest = (
                    short_put.get(
                        "open_interest",
                        0.0,
                    )
                    + long_put.get(
                        "open_interest",
                        0.0,
                    )
                )

                combined_volume = (
                    short_put.get(
                        "volume",
                        0.0,
                    )
                    + long_put.get(
                        "volume",
                        0.0,
                    )
                )

                combined_relative_spread = (
                    _relative_spread(
                        short_put
                    )
                    + _relative_spread(
                        long_put
                    )
                )

                rank = (
                    abs(
                        underlying
                        - short_put[
                            "strike"
                        ]
                    ),
                    width,
                    -combined_open_interest,
                    -combined_volume,
                    combined_relative_spread,
                    -credit,
                )

                candidates.append((
                    rank,
                    short_put,
                    long_put,
                    credit,
                    width,
                    maximum_loss,
                ))

    if not candidates:
        raise MissingStrategySelectionError(
            "no_valid_bull_put_spread"
        )

    (
        _,
        short_put,
        long_put,
        credit,
        width,
        maximum_loss,
    ) = sorted(
        candidates,
        key=lambda item: item[0],
    )[0]

    expiration = short_put[
        "expiration"
    ]

    if (
        long_put["expiration"]
        != expiration
    ):
        raise MissingStrategySelectionError(
            "mixed_expirations"
        )

    maximum_profit = (
        credit
        * CONTRACT_MULTIPLIER
    )

    days_to_expiry = _days_to_expiry(
        provider_payload,
        [
            short_put,
            long_put,
        ],
    )

    result = _base_result(
        strategy="bull_put_spread",
        provider_payload=provider_payload,
        expiration=expiration,
        days_to_expiry=days_to_expiry,
        contract_legs=[
            _leg_payload(
                short_put,
                "SELL",
            ),
            _leg_payload(
                long_put,
                "BUY",
            ),
        ],
    )

    result.update({
        "net_premium_per_share": (
            round(
                credit,
                8,
            )
        ),
        "gross_debit_per_share": (
            round(
                long_put["mid"],
                8,
            )
        ),
        "gross_credit_per_share": (
            round(
                short_put["mid"],
                8,
            )
        ),
        "spread_width": round(
            width,
            8,
        ),
        "maximum_loss_per_contract": (
            round(
                maximum_loss,
                6,
            )
        ),
        "maximum_profit_per_contract": (
            round(
                maximum_profit,
                6,
            )
        ),
        "maximum_profit_profile": (
            "DEFINED_CREDIT"
        ),
        "assignment_notional_per_contract": (
            round(
                short_put["strike"]
                * CONTRACT_MULTIPLIER,
                6,
            )
        ),
    })

    return result


def select_missing_strategy_v3(
    *,
    strategy: str,
    provider_payload: dict[str, Any],
) -> dict[str, Any]:
    normalized_strategy = _normalized_text(
        strategy
    ).lower()

    if normalized_strategy == "long_call":
        return select_long_call_v3(
            provider_payload
        )

    if (
        normalized_strategy
        == "bull_put_spread"
    ):
        return select_bull_put_spread_v3(
            provider_payload
        )

    raise MissingStrategySelectionError(
        f"unsupported_extended_strategy:"
        f"{normalized_strategy or 'missing'}"
    )
