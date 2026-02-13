#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

@dataclass
class SizingResult:
    qty: float
    notional: float
    warnings: list

def size_qty_from_budget(
    *,
    size_usd: float,
    price: float,
    caps: Dict[str, Any],
    min_notional_usd: float = 50.0
) -> SizingResult:
    warnings = []
    if price <= 0 or size_usd <= 0:
        return SizingResult(qty=0.0, notional=0.0, warnings=["invalid_price_or_size"])

    max_order_notional = float(caps.get("max_order_notional_usd") or 0.0)
    if max_order_notional > 0 and size_usd > max_order_notional:
        warnings.append("clamped_to_max_order_notional")
        size_usd = max_order_notional

    if size_usd < min_notional_usd:
        warnings.append("below_min_notional")
        return SizingResult(qty=0.0, notional=0.0, warnings=warnings)

    qty = size_usd / price

    # Stocks: qty must be integer (no fractional shares in many brokers)
    # V0: round down to int
    qty_int = int(qty)
    if qty_int <= 0:
        warnings.append("qty_rounded_to_zero")
        return SizingResult(qty=0.0, notional=0.0, warnings=warnings)

    notional = qty_int * price
    return SizingResult(qty=float(qty_int), notional=float(notional), warnings=warnings)
