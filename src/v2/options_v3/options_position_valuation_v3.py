from __future__ import annotations

import math
from typing import Any


CONTRACT_MULTIPLIER = 100


class OptionsPositionValuationError(RuntimeError):
    pass


def _finite_number(
    value: Any,
    field: str,
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise OptionsPositionValuationError(
            f"{field}: numeric value required"
        ) from exc

    if not math.isfinite(result):
        raise OptionsPositionValuationError(
            f"{field}: finite value required"
        )

    if positive and result <= 0.0:
        raise OptionsPositionValuationError(
            f"{field}: positive value required"
        )

    if non_negative and result < 0.0:
        raise OptionsPositionValuationError(
            f"{field}: non-negative value required"
        )

    return result


def _canonical_position_legs(
    position: dict[str, Any],
) -> list[dict[str, Any]]:
    legs = position.get("contract_legs")

    if not isinstance(legs, list) or not legs:
        raise OptionsPositionValuationError(
            "position.contract_legs: non-empty list required"
        )

    result = []

    for index, leg in enumerate(legs):
        if not isinstance(leg, dict):
            raise OptionsPositionValuationError(
                f"position.contract_legs[{index}]: dict required"
            )

        symbol = str(
            leg.get("contract_symbol") or ""
        ).strip()

        side = str(
            leg.get("side") or ""
        ).strip().upper()

        if not symbol:
            raise OptionsPositionValuationError(
                f"position.contract_legs[{index}].contract_symbol: "
                "required"
            )

        if side not in {"BUY", "SELL"}:
            raise OptionsPositionValuationError(
                f"position.contract_legs[{index}].side: "
                "BUY or SELL required"
            )

        entry_bid = _finite_number(
            leg.get("bid"),
            f"position.contract_legs[{index}].bid",
            non_negative=True,
        )

        entry_ask = _finite_number(
            leg.get("ask"),
            f"position.contract_legs[{index}].ask",
            non_negative=True,
        )

        if entry_ask < entry_bid:
            raise OptionsPositionValuationError(
                f"position.contract_legs[{index}]: "
                "entry ask lower than bid"
            )

        if side == "BUY" and entry_ask <= 0.0:
            raise OptionsPositionValuationError(
                f"position.contract_legs[{index}].ask: "
                "positive BUY entry ask required"
            )

        if side == "SELL" and entry_bid <= 0.0:
            raise OptionsPositionValuationError(
                f"position.contract_legs[{index}].bid: "
                "positive SELL entry bid required"
            )

        result.append({
            "contract_symbol": symbol,
            "side": side,
            "entry_bid": entry_bid,
            "entry_ask": entry_ask,
        })

    symbols = [
        leg["contract_symbol"]
        for leg in result
    ]

    if len(symbols) != len(set(symbols)):
        raise OptionsPositionValuationError(
            "position.contract_legs: duplicate contract symbol"
        )

    return result


def _canonical_current_quotes(
    quotes: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not isinstance(quotes, list) or not quotes:
        raise OptionsPositionValuationError(
            "quotes: non-empty list required"
        )

    result = {}

    for index, quote in enumerate(quotes):
        if not isinstance(quote, dict):
            raise OptionsPositionValuationError(
                f"quotes[{index}]: dict required"
            )

        symbol = str(
            quote.get("contract_symbol") or ""
        ).strip()

        if not symbol:
            raise OptionsPositionValuationError(
                f"quotes[{index}].contract_symbol: required"
            )

        if symbol in result:
            raise OptionsPositionValuationError(
                f"quotes: duplicate contract symbol {symbol}"
            )

        currency = str(
            quote.get("currency") or ""
        ).strip().upper()

        if currency != "USD":
            raise OptionsPositionValuationError(
                f"quotes[{index}].currency: USD required"
            )

        bid = _finite_number(
            quote.get("bid"),
            f"quotes[{index}].bid",
            non_negative=True,
        )

        ask = _finite_number(
            quote.get("ask"),
            f"quotes[{index}].ask",
            non_negative=True,
        )

        if ask < bid:
            raise OptionsPositionValuationError(
                f"quotes[{index}]: ask lower than bid"
            )

        if bid <= 0.0 and ask <= 0.0:
            raise OptionsPositionValuationError(
                f"quotes[{index}]: no executable quote"
            )

        result[symbol] = {
            "contract_symbol": symbol,
            "bid": bid,
            "ask": ask,
            "currency": "USD",
            "provider": quote.get("provider"),
            "provider_timestamp": quote.get(
                "provider_timestamp"
            ),
            "last_trade_date": quote.get(
                "last_trade_date"
            ),
        }

    return result


def value_open_position_v3(
    position: dict[str, Any],
    current_quotes: list[dict[str, Any]],
    *,
    usd_eur_rate: float,
    fx_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(position, dict):
        raise OptionsPositionValuationError(
            "position: dict required"
        )

    if str(
        position.get("status") or ""
    ).strip().upper() != "OPEN":
        raise OptionsPositionValuationError(
            "position.status: OPEN required"
        )

    quantity = int(
        _finite_number(
            position.get("contract_quantity"),
            "position.contract_quantity",
            positive=True,
        )
    )

    if float(quantity) != float(
        position.get("contract_quantity")
    ):
        raise OptionsPositionValuationError(
            "position.contract_quantity: integer required"
        )

    fx = _finite_number(
        usd_eur_rate,
        "usd_eur_rate",
        positive=True,
    )

    if not isinstance(fx_provenance, dict) or not fx_provenance:
        raise OptionsPositionValuationError(
            "fx_provenance: non-empty dict required"
        )

    provenance_rate = fx_provenance.get("rate")

    if provenance_rate is not None:
        provenance_rate_value = _finite_number(
            provenance_rate,
            "fx_provenance.rate",
            positive=True,
        )

        if not math.isclose(
            provenance_rate_value,
            fx,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise OptionsPositionValuationError(
                "fx_provenance.rate: inconsistent with usd_eur_rate"
            )

    legs = _canonical_position_legs(position)
    quotes = _canonical_current_quotes(
        current_quotes
    )

    expected_symbols = {
        leg["contract_symbol"]
        for leg in legs
    }
    quote_symbols = set(quotes)

    if quote_symbols != expected_symbols:
        missing = sorted(
            expected_symbols - quote_symbols
        )
        unexpected = sorted(
            quote_symbols - expected_symbols
        )

        raise OptionsPositionValuationError(
            "quotes: exact contract identity required; "
            f"missing={missing}; unexpected={unexpected}"
        )

    leg_valuations = []
    pnl_per_share_usd = 0.0

    for leg in legs:
        quote = quotes[
            leg["contract_symbol"]
        ]

        if leg["side"] == "BUY":
            opening_cashflow = -leg["entry_ask"]
            liquidation_cashflow = quote["bid"]
        else:
            opening_cashflow = leg["entry_bid"]
            liquidation_cashflow = -quote["ask"]

        leg_pnl = (
            opening_cashflow
            + liquidation_cashflow
        )

        pnl_per_share_usd += leg_pnl

        leg_valuations.append({
            "contract_symbol": (
                leg["contract_symbol"]
            ),
            "side": leg["side"],
            "entry_bid_usd": round(
                leg["entry_bid"], 8
            ),
            "entry_ask_usd": round(
                leg["entry_ask"], 8
            ),
            "current_bid_usd": round(
                quote["bid"], 8
            ),
            "current_ask_usd": round(
                quote["ask"], 8
            ),
            "opening_cashflow_per_share_usd": round(
                opening_cashflow, 8
            ),
            "liquidation_cashflow_per_share_usd": round(
                liquidation_cashflow, 8
            ),
            "pnl_per_share_usd": round(
                leg_pnl, 8
            ),
        })

    pnl_usd = (
        pnl_per_share_usd
        * CONTRACT_MULTIPLIER
        * quantity
    )

    pnl_eur = pnl_usd * fx

    return {
        "position_id": position.get(
            "position_id"
        ),
        "structure_id": position.get(
            "structure_id"
        ),
        "contract_quantity": quantity,
        "contract_multiplier": (
            CONTRACT_MULTIPLIER
        ),
        "leg_count": len(legs),
        "leg_valuations": leg_valuations,
        "pnl_per_share_usd": round(
            pnl_per_share_usd, 8
        ),
        "pnl_usd": round(
            pnl_usd, 8
        ),
        "usd_eur_rate": round(
            fx, 12
        ),
        "pnl_eur": round(
            pnl_eur, 8
        ),
        "pnl_pct": None,
        "pnl_pct_status": (
            "ENTRY_RISK_EUR_PROVENANCE_REQUIRED"
        ),
        "valuation_currency": "EUR",
        "contract_economics_currency": "USD",
        "fx_provenance": dict(
            fx_provenance or {}
        ),
        "valuation_method": (
            "EXECUTABLE_BID_ASK_LIQUIDATION"
        ),
        "read_only_valuation": True,
        "real_execution_allowed": False,
    }
