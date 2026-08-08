#!/usr/bin/env python3
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class SizingResult:
    qty: float
    notional: float
    warnings: list
    policy: str = "integer_floor"
    quantity_step: float = 1.0


def _floor_to_step(value: float, step: float) -> float:
    """
    Floor a quantity to the broker step without binary-float
    rounding errors.

    Decimal(str(...)) is deliberately used so scientific notation
    such as 1e-06 remains a valid six-decimal quantity step.
    """
    try:
        value_decimal = Decimal(str(value))
        step_decimal = Decimal(str(step))
    except (InvalidOperation, ValueError, TypeError):
        return 0.0

    if value_decimal <= 0 or step_decimal <= 0:
        return 0.0

    units = (
        value_decimal / step_decimal
    ).to_integral_value(
        rounding=ROUND_FLOOR
    )

    result = units * step_decimal

    return float(result)


def size_qty_from_budget(
    *,
    size_usd: float,
    price: float,
    caps: Dict[str, Any],
    min_notional_usd: float = 50.0,
    broker_capabilities: Dict[str, Any] | None = None,
) -> SizingResult:
    warnings = []

    try:
        size_usd = float(size_usd)
        price = float(price)
    except Exception:
        return SizingResult(
            qty=0.0,
            notional=0.0,
            warnings=["invalid_price_or_size"],
        )

    if price <= 0 or size_usd <= 0:
        return SizingResult(
            qty=0.0,
            notional=0.0,
            warnings=["invalid_price_or_size"],
        )

    caps = caps if isinstance(caps, dict) else {}
    capabilities = (
        broker_capabilities
        if isinstance(broker_capabilities, dict)
        else {}
    )

    max_order_notional = float(
        caps.get("max_order_notional_usd") or 0.0
    )

    if (
        max_order_notional > 0
        and size_usd > max_order_notional
    ):
        warnings.append("clamped_to_max_order_notional")
        size_usd = max_order_notional

    broker_min_notional = float(
        capabilities.get("minimum_notional_usd") or 0.0
    )

    effective_min_notional = max(
        float(min_notional_usd or 0.0),
        broker_min_notional,
    )

    if size_usd < effective_min_notional:
        warnings.append("below_min_notional")
        return SizingResult(
            qty=0.0,
            notional=0.0,
            warnings=warnings,
        )

    fractional_quantity = bool(
        capabilities.get("fractional_quantity", False)
    )

    if fractional_quantity:
        policy = "broker_quantity_step"

        quantity_step = float(
            capabilities.get("quantity_step") or 0.000001
        )

        minimum_quantity = float(
            capabilities.get("minimum_quantity")
            or quantity_step
        )
    else:
        policy = "integer_floor"
        quantity_step = 1.0
        minimum_quantity = 1.0

    if quantity_step <= 0:
        warnings.append("invalid_quantity_step")
        return SizingResult(
            qty=0.0,
            notional=0.0,
            warnings=warnings,
            policy=policy,
            quantity_step=quantity_step,
        )

    raw_qty = size_usd / price
    selected_qty = _floor_to_step(
        raw_qty,
        quantity_step,
    )

    if selected_qty < minimum_quantity:
        warnings.append(
            "qty_below_broker_minimum"
            if fractional_quantity
            else "qty_rounded_to_zero"
        )

        return SizingResult(
            qty=0.0,
            notional=0.0,
            warnings=warnings,
            policy=policy,
            quantity_step=quantity_step,
        )

    notional = selected_qty * price

    if notional < effective_min_notional:
        warnings.append("notional_below_minimum_after_rounding")

        return SizingResult(
            qty=0.0,
            notional=0.0,
            warnings=warnings,
            policy=policy,
            quantity_step=quantity_step,
        )

    if selected_qty < raw_qty:
        warnings.append(
            "rounded_down_to_quantity_step"
            if fractional_quantity
            else "rounded_down_to_whole_share"
        )

    return SizingResult(
        qty=float(selected_qty),
        notional=float(notional),
        warnings=warnings,
        policy=policy,
        quantity_step=float(quantity_step),
    )
