from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Minimal ruleset for US equities (IBKR-friendly baseline).
# Later: per-exchange rules, per-asset rules, and broker-specific constraints.

@dataclass
class ValidationResult:
    ok: bool
    reasons: List[str]
    normalized_order: Dict[str, Any]

def _is_number(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _round_to_tick(price: float, tick: float) -> float:
    if tick <= 0:
        return price
    # round to nearest tick (can change to floor depending on policy)
    return round(price / tick) * tick

def validate_us_equity_order(
    order: Dict[str, Any],
    *,
    now_utc: Optional[datetime] = None,
    allow_market: bool = True,
    min_notional_usd: float = 10.0,
    min_qty: float = 1.0,
    max_qty: float = 10_000.0,
    tick_size: float = 0.01,
    lot_size: float = 1.0,
    market_open: bool = True,
) -> ValidationResult:
    """
    Validate and normalize a US equity order.
    This is deliberately conservative; broker adapters can add stricter checks.

    Expected fields (subset):
      - symbol (str)
      - side: BUY/SELL
      - qty (number)
      - order_type: MARKET/LIMIT
      - price (number) for LIMIT
      - time_in_force: DAY/GTC (optional)
      - notional_usd (optional) if available
    """
    reasons: List[str] = []
    o = dict(order or {})

    # Required
    symbol = str(o.get("symbol", "")).strip().upper()
    if not symbol:
        reasons.append("missing_symbol")
    else:
        o["symbol"] = symbol

    side = str(o.get("side", "")).strip().upper()
    if side not in {"BUY", "SELL"}:
        reasons.append("invalid_side")
    else:
        o["side"] = side

    order_type = str(o.get("order_type", "MARKET")).strip().upper()
    if order_type not in {"MARKET", "LIMIT"}:
        reasons.append("invalid_order_type")
    if order_type == "MARKET" and not allow_market:
        reasons.append("market_orders_disabled")
    o["order_type"] = order_type

    tif = str(o.get("time_in_force", "DAY")).strip().upper()
    if tif not in {"DAY", "GTC"}:
        reasons.append("invalid_time_in_force")
    o["time_in_force"] = tif

    # Qty / lot size
    qty = o.get("qty")
    if not _is_number(qty):
        reasons.append("invalid_qty")
        qty_f = 0.0
    else:
        qty_f = float(qty)
        if qty_f < min_qty:
            reasons.append("qty_below_min")
        if qty_f > max_qty:
            reasons.append("qty_above_max")
        # lot size integer shares for equities
        if lot_size > 0:
            # enforce multiple of lot_size
            rem = qty_f % lot_size
            if rem != 0:
                # normalize by rounding down to closest lot
                normalized = qty_f - rem
                if normalized < min_qty:
                    reasons.append("qty_not_multiple_of_lot")
                else:
                    o["qty"] = normalized
            else:
                o["qty"] = qty_f
        else:
            o["qty"] = qty_f

    # Price / tick size for LIMIT
    price = o.get("price")
    if order_type == "LIMIT":
        if not _is_number(price):
            reasons.append("missing_or_invalid_price_for_limit")
        else:
            p = float(price)
            if p <= 0:
                reasons.append("price_non_positive")
            else:
                o["price"] = _round_to_tick(p, tick_size)
    else:
        o["price"] = None

    # Market hours gate (handled higher level too)
    if not market_open:
        reasons.append("market_closed")

    # Notional check (if price known or notional provided)
    notional = o.get("notional_usd")
    notional_f = None
    if _is_number(notional):
        notional_f = float(notional)
    elif order_type == "LIMIT" and _is_number(o.get("price")) and _is_number(o.get("qty")):
        notional_f = float(o["price"]) * float(o["qty"])

    if notional_f is not None and notional_f < min_notional_usd:
        reasons.append("notional_below_min")

    ok = len(reasons) == 0
    return ValidationResult(ok=ok, reasons=reasons, normalized_order=o)

def validate_execution_plan(
    plan: Dict[str, Any],
    *,
    market_open: bool = True,
    tick_size: float = 0.01,
    lot_size: float = 1.0,
    min_notional_usd: float = 10.0,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate all orders in an execution plan.
    Returns (ok, orders_out) where each order has:
      - validation_ok
      - validation_reasons
      - normalized fields
    """
    orders = list((plan or {}).get("orders", []) or [])
    out: List[Dict[str, Any]] = []
    all_ok = True

    for o in orders:
        res = validate_us_equity_order(
            o,
            market_open=market_open,
            tick_size=tick_size,
            lot_size=lot_size,
            min_notional_usd=min_notional_usd,
        )
        od = dict(res.normalized_order)
        od["validation_ok"] = res.ok
        od["validation_reasons"] = res.reasons
        out.append(od)
        if not res.ok:
            all_ok = False

    return all_ok, out
