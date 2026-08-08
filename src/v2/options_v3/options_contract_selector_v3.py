from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import math
from options_missing_strategy_selector_v3 import EXTENDED_STRATEGIES, MissingStrategySelectionError, select_missing_strategy_v3


SUPPORTED_STRATEGIES = {
    "covered_call",
    "cash_secured_put",
    "bull_call_spread",
    "bear_put_spread",
    "neutral_spread",
}


class ContractSelectionError(RuntimeError):
    """Fail-closed error raised when no valid structure can be selected."""


@dataclass(frozen=True)
class SelectedLegV3:
    side: str
    option_type: str
    contract_symbol: str
    expiration: str
    days_to_expiry: int
    strike: float
    bid: float
    ask: float
    mid: float
    implied_volatility: float
    volume: float | None
    open_interest: float | None
    underlying_price: float
    provider: str
    provider_timestamp: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "side": self.side,
            "option_type": self.option_type,
            "contract_symbol": self.contract_symbol,
            "expiration": self.expiration,
            "days_to_expiry": self.days_to_expiry,
            "strike": self.strike,
            "bid": self.bid,
            "ask": self.ask,
            "mid": self.mid,
            "implied_volatility": self.implied_volatility,
            "volume": self.volume,
            "open_interest": self.open_interest,
            "underlying_price": self.underlying_price,
            "provider": self.provider,
            "provider_timestamp": self.provider_timestamp,
        }


def _finite_float(
    value: Any,
    *,
    field: str,
    positive: bool = False,
    non_negative: bool = False,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractSelectionError(
            f"{field}: invalid numeric value"
        ) from exc

    if not math.isfinite(result):
        raise ContractSelectionError(
            f"{field}: non-finite numeric value"
        )

    if positive and result <= 0:
        raise ContractSelectionError(
            f"{field}: positive value required"
        )

    if non_negative and result < 0:
        raise ContractSelectionError(
            f"{field}: non-negative value required"
        )

    return result


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def _normalize_contract(
    contract: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ContractSelectionError(
            "contract: dictionary required"
        )

    option_type = str(
        contract.get("option_type") or ""
    ).upper()

    if option_type not in {"CALL", "PUT"}:
        raise ContractSelectionError(
            "option_type: CALL or PUT required"
        )

    contract_symbol = str(
        contract.get("contract_symbol") or ""
    ).strip()

    if not contract_symbol:
        raise ContractSelectionError(
            "contract_symbol: required"
        )

    expiration = str(
        contract.get("expiration") or ""
    ).strip()

    if not expiration:
        raise ContractSelectionError(
            "expiration: required"
        )

    provider = str(
        contract.get("provider") or ""
    ).strip()

    if not provider:
        raise ContractSelectionError(
            "provider: required"
        )

    provider_timestamp = str(
        contract.get("provider_timestamp") or ""
    ).strip()

    if not provider_timestamp:
        raise ContractSelectionError(
            "provider_timestamp: required"
        )

    days_to_expiry = int(
        _finite_float(
            contract.get("days_to_expiry"),
            field="days_to_expiry",
            positive=True,
        )
    )

    strike = _finite_float(
        contract.get("strike"),
        field="strike",
        positive=True,
    )

    bid = _finite_float(
        contract.get("bid"),
        field="bid",
        positive=True,
    )

    ask = _finite_float(
        contract.get("ask"),
        field="ask",
        positive=True,
    )

    mid = _finite_float(
        contract.get("mid"),
        field="mid",
        positive=True,
    )

    implied_volatility = _finite_float(
        contract.get("implied_volatility"),
        field="implied_volatility",
        positive=True,
    )

    underlying_price = _finite_float(
        contract.get("underlying_price"),
        field="underlying_price",
        positive=True,
    )

    if ask < bid:
        raise ContractSelectionError(
            "ask lower than bid"
        )

    expected_mid = (bid + ask) / 2.0

    if abs(mid - expected_mid) > 1e-5:
        raise ContractSelectionError(
            "mid inconsistent with bid and ask"
        )

    return {
        **contract,
        "option_type": option_type,
        "contract_symbol": contract_symbol,
        "expiration": expiration,
        "days_to_expiry": days_to_expiry,
        "strike": strike,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "implied_volatility": implied_volatility,
        "underlying_price": underlying_price,
        "volume": _optional_float(
            contract.get("volume")
        ),
        "open_interest": _optional_float(
            contract.get("open_interest")
        ),
        "provider": provider,
        "provider_timestamp": provider_timestamp,
    }


def _normalized_contracts(
    provider_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(provider_payload, dict):
        raise ContractSelectionError(
            "provider_payload: dictionary required"
        )

    contracts = provider_payload.get("contracts")

    if not isinstance(contracts, list):
        raise ContractSelectionError(
            "provider_payload.contracts: list required"
        )

    normalized: list[dict[str, Any]] = []
    rejected_count = 0

    for contract in contracts:
        try:
            normalized.append(
                _normalize_contract(contract)
            )
        except ContractSelectionError:
            rejected_count += 1

    if not normalized:
        raise ContractSelectionError(
            "no valid normalized contract available"
        )

    expirations = {
        contract["expiration"]
        for contract in normalized
    }

    if len(expirations) != 1:
        raise ContractSelectionError(
            "provider payload contains multiple expirations"
        )

    underlying_prices = {
        round(
            contract["underlying_price"],
            8,
        )
        for contract in normalized
    }

    if len(underlying_prices) != 1:
        raise ContractSelectionError(
            "provider payload contains inconsistent underlying prices"
        )

    return normalized


def _leg(
    contract: dict[str, Any],
    *,
    side: str,
) -> SelectedLegV3:
    normalized_side = str(side).upper()

    if normalized_side not in {"BUY", "SELL"}:
        raise ContractSelectionError(
            "side: BUY or SELL required"
        )

    return SelectedLegV3(
        side=normalized_side,
        option_type=contract["option_type"],
        contract_symbol=contract[
            "contract_symbol"
        ],
        expiration=contract["expiration"],
        days_to_expiry=contract[
            "days_to_expiry"
        ],
        strike=contract["strike"],
        bid=contract["bid"],
        ask=contract["ask"],
        mid=contract["mid"],
        implied_volatility=contract[
            "implied_volatility"
        ],
        volume=contract.get("volume"),
        open_interest=contract.get(
            "open_interest"
        ),
        underlying_price=contract[
            "underlying_price"
        ],
        provider=contract["provider"],
        provider_timestamp=contract[
            "provider_timestamp"
        ],
    )


def _calls(
    contracts: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        [
            contract
            for contract in contracts
            if contract["option_type"] == "CALL"
        ],
        key=lambda contract: (
            contract["strike"],
            contract["contract_symbol"],
        ),
    )


def _puts(
    contracts: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        [
            contract
            for contract in contracts
            if contract["option_type"] == "PUT"
        ],
        key=lambda contract: (
            contract["strike"],
            contract["contract_symbol"],
        ),
    )


def _nearest(
    contracts: Iterable[dict[str, Any]],
    *,
    target_strike: float,
) -> dict[str, Any]:
    candidates = list(contracts)

    if not candidates:
        raise ContractSelectionError(
            "no contract candidate available"
        )

    return min(
        candidates,
        key=lambda contract: (
            abs(
                contract["strike"]
                - target_strike
            ),
            contract["strike"],
            contract["contract_symbol"],
        ),
    )


def _nearest_above(
    contracts: Iterable[dict[str, Any]],
    *,
    threshold: float,
) -> dict[str, Any]:
    candidates = [
        contract
        for contract in contracts
        if contract["strike"] > threshold
    ]

    if not candidates:
        raise ContractSelectionError(
            "no liquid strike above threshold"
        )

    return min(
        candidates,
        key=lambda contract: (
            contract["strike"] - threshold,
            contract["contract_symbol"],
        ),
    )


def _nearest_below(
    contracts: Iterable[dict[str, Any]],
    *,
    threshold: float,
) -> dict[str, Any]:
    candidates = [
        contract
        for contract in contracts
        if contract["strike"] < threshold
    ]

    if not candidates:
        raise ContractSelectionError(
            "no liquid strike below threshold"
        )

    return min(
        candidates,
        key=lambda contract: (
            threshold - contract["strike"],
            contract["contract_symbol"],
        ),
    )


def _premium_for_leg(
    leg: SelectedLegV3,
) -> float:
    if leg.side == "BUY":
        return -leg.ask

    return leg.bid


def _common_structure(
    *,
    strategy: str,
    legs: list[SelectedLegV3],
) -> dict[str, Any]:
    if not legs:
        raise ContractSelectionError(
            "contract structure requires at least one leg"
        )

    expirations = {
        leg.expiration
        for leg in legs
    }

    if len(expirations) != 1:
        raise ContractSelectionError(
            "all strategy legs must share the same expiration"
        )

    provider_names = {
        leg.provider
        for leg in legs
    }

    if len(provider_names) != 1:
        raise ContractSelectionError(
            "all strategy legs must share the same provider"
        )

    underlying_prices = {
        round(
            leg.underlying_price,
            8,
        )
        for leg in legs
    }

    if len(underlying_prices) != 1:
        raise ContractSelectionError(
            "all strategy legs must share the same underlying price"
        )

    net_premium_per_share = sum(
        _premium_for_leg(leg)
        for leg in legs
    )

    gross_debit_per_share = sum(
        leg.ask
        for leg in legs
        if leg.side == "BUY"
    )

    gross_credit_per_share = sum(
        leg.bid
        for leg in legs
        if leg.side == "SELL"
    )

    return {
        "strategy": strategy,
        "provider": legs[0].provider,
        "provider_timestamp": legs[
            0
        ].provider_timestamp,
        "expiration": legs[0].expiration,
        "days_to_expiry": legs[
            0
        ].days_to_expiry,
        "underlying_price": legs[
            0
        ].underlying_price,
        "leg_count": len(legs),
        "contract_legs": [
            leg.as_dict()
            for leg in legs
        ],
        "net_premium_per_share": round(
            net_premium_per_share,
            8,
        ),
        "gross_debit_per_share": round(
            gross_debit_per_share,
            8,
        ),
        "gross_credit_per_share": round(
            gross_credit_per_share,
            8,
        ),
        "selection_status": "SELECTED",
        "simulation_only": True,
        "real_execution_allowed": False,
    }


def _select_covered_call(
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    calls = _calls(contracts)

    if not calls:
        raise ContractSelectionError(
            "covered_call: no calls available"
        )

    spot = calls[0]["underlying_price"]

    selected = _nearest_above(
        calls,
        threshold=spot,
    )

    result = _common_structure(
        strategy="covered_call",
        legs=[
            _leg(
                selected,
                side="SELL",
            )
        ],
    )

    result["strike_relation"] = "OTM_ABOVE_SPOT"
    result["covered_equity_required"] = True
    result["maximum_loss_profile"] = (
        "underlying_equity_downside_less_premium"
    )

    return result


def _select_cash_secured_put(
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    puts = _puts(contracts)

    if not puts:
        raise ContractSelectionError(
            "cash_secured_put: no puts available"
        )

    spot = puts[0]["underlying_price"]

    selected = _nearest_below(
        puts,
        threshold=spot,
    )

    result = _common_structure(
        strategy="cash_secured_put",
        legs=[
            _leg(
                selected,
                side="SELL",
            )
        ],
    )

    result["strike_relation"] = "OTM_BELOW_SPOT"
    result["cash_secured_required"] = True
    result["assignment_notional_per_contract"] = round(
        selected["strike"] * 100,
        8,
    )

    return result


def _select_bull_call_spread(
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    calls = _calls(contracts)

    if len(calls) < 2:
        raise ContractSelectionError(
            "bull_call_spread: at least two calls required"
        )

    spot = calls[0]["underlying_price"]

    long_call = _nearest(
        calls,
        target_strike=spot,
    )

    short_call = _nearest_above(
        calls,
        threshold=long_call["strike"],
    )

    if short_call["strike"] <= long_call["strike"]:
        raise ContractSelectionError(
            "bull_call_spread: invalid strike ordering"
        )

    result = _common_structure(
        strategy="bull_call_spread",
        legs=[
            _leg(
                long_call,
                side="BUY",
            ),
            _leg(
                short_call,
                side="SELL",
            ),
        ],
    )

    spread_width = (
        short_call["strike"]
        - long_call["strike"]
    )

    net_debit = (
        long_call["ask"]
        - short_call["bid"]
    )

    if net_debit <= 0:
        raise ContractSelectionError(
            "bull_call_spread: positive net debit required"
        )

    if net_debit >= spread_width:
        raise ContractSelectionError(
            "bull_call_spread: net debit exceeds or equals spread width"
        )

    result["spread_width"] = round(
        spread_width,
        8,
    )
    result["net_debit_per_share"] = round(
        net_debit,
        8,
    )
    result["maximum_loss_per_contract"] = round(
        net_debit * 100,
        8,
    )
    result["maximum_profit_per_contract"] = round(
        (
            spread_width
            - net_debit
        )
        * 100,
        8,
    )
    result["defined_risk"] = True

    return result


def _select_bear_put_spread(
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    puts = _puts(contracts)

    if len(puts) < 2:
        raise ContractSelectionError(
            "bear_put_spread: at least two puts required"
        )

    spot = puts[0]["underlying_price"]

    long_put = _nearest(
        puts,
        target_strike=spot,
    )

    short_put = _nearest_below(
        puts,
        threshold=long_put["strike"],
    )

    if short_put["strike"] >= long_put["strike"]:
        raise ContractSelectionError(
            "bear_put_spread: invalid strike ordering"
        )

    result = _common_structure(
        strategy="bear_put_spread",
        legs=[
            _leg(
                long_put,
                side="BUY",
            ),
            _leg(
                short_put,
                side="SELL",
            ),
        ],
    )

    spread_width = (
        long_put["strike"]
        - short_put["strike"]
    )

    net_debit = (
        long_put["ask"]
        - short_put["bid"]
    )

    if net_debit <= 0:
        raise ContractSelectionError(
            "bear_put_spread: positive net debit required"
        )

    if net_debit >= spread_width:
        raise ContractSelectionError(
            "bear_put_spread: net debit exceeds or equals spread width"
        )

    result["spread_width"] = round(
        spread_width,
        8,
    )
    result["net_debit_per_share"] = round(
        net_debit,
        8,
    )
    result["maximum_loss_per_contract"] = round(
        net_debit * 100,
        8,
    )
    result["maximum_profit_per_contract"] = round(
        (
            spread_width
            - net_debit
        )
        * 100,
        8,
    )
    result["defined_risk"] = True

    return result


def _select_neutral_spread(
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    calls = _calls(contracts)

    if len(calls) < 2:
        raise ContractSelectionError(
            "neutral_spread: at least two calls required"
        )

    spot = calls[0]["underlying_price"]

    long_call = _nearest(
        calls,
        target_strike=spot,
    )

    short_call = _nearest_above(
        calls,
        threshold=long_call["strike"],
    )

    spread_width = (
        short_call["strike"]
        - long_call["strike"]
    )

    net_debit = (
        long_call["ask"]
        - short_call["bid"]
    )

    if spread_width <= 0:
        raise ContractSelectionError(
            "neutral_spread: positive spread width required"
        )

    if net_debit <= 0:
        raise ContractSelectionError(
            "neutral_spread: positive net debit required"
        )

    if net_debit >= spread_width:
        raise ContractSelectionError(
            "neutral_spread: net debit exceeds or equals spread width"
        )

    result = _common_structure(
        strategy="neutral_spread",
        legs=[
            _leg(
                long_call,
                side="BUY",
            ),
            _leg(
                short_call,
                side="SELL",
            ),
        ],
    )

    result["spread_width"] = round(
        spread_width,
        8,
    )
    result["net_debit_per_share"] = round(
        net_debit,
        8,
    )
    result["maximum_loss_per_contract"] = round(
        net_debit * 100,
        8,
    )
    result["maximum_profit_per_contract"] = round(
        (
            spread_width
            - net_debit
        )
        * 100,
        8,
    )
    result["defined_risk"] = True
    result["strategy_semantics"] = (
        "neutral_defined_risk_call_vertical"
    )

    return result


def select_contract_structure_v3(
    *,
    strategy: str,
    provider_payload: dict[str, Any],
) -> dict[str, Any]:
    normalized_strategy = str(
        strategy or ""
    ).strip().lower()

    if normalized_strategy not in SUPPORTED_STRATEGIES:
        raise ContractSelectionError(
            f"unsupported strategy: {strategy!r}"
        )

    contracts = _normalized_contracts(
        provider_payload
    )

    selectors = {
        "covered_call": _select_covered_call,
        "cash_secured_put": (
            _select_cash_secured_put
        ),
        "bull_call_spread": (
            _select_bull_call_spread
        ),
        "bear_put_spread": (
            _select_bear_put_spread
        ),
        "neutral_spread": (
            _select_neutral_spread
        ),
    }

    result = selectors[
        normalized_strategy
    ](contracts)

    result["source_contract_count"] = len(
        contracts
    )
    result["selector_engine"] = (
        "options_contract_selector_v3"
    )
    result["selector_version"] = "3.0.0"

    return result


__all__ = [
    "ContractSelectionError",
    "SUPPORTED_STRATEGIES",
    "SelectedLegV3",
    "select_contract_structure_v3",
]


# =========================================================
# RC2-51 — Options V3 missing-strategy extension
# =========================================================

_select_contract_structure_v3_base = select_contract_structure_v3

try:
    SUPPORTED_STRATEGIES = (
        set(SUPPORTED_STRATEGIES)
        | set(EXTENDED_STRATEGIES)
    )
except NameError:
    SUPPORTED_STRATEGIES = set(
        EXTENDED_STRATEGIES
    )


def select_contract_structure_v3(
    *,
    strategy,
    provider_payload,
):
    normalized_strategy = str(
        strategy or ""
    ).strip().lower()

    if normalized_strategy in EXTENDED_STRATEGIES:
        try:
            return select_missing_strategy_v3(
                strategy=normalized_strategy,
                provider_payload=provider_payload,
            )

        except MissingStrategySelectionError as exc:
            try:
                raise ContractSelectionError(
                    str(exc)
                ) from exc
            except NameError:
                raise

    return _select_contract_structure_v3_base(
        strategy=normalized_strategy,
        provider_payload=provider_payload,
    )

