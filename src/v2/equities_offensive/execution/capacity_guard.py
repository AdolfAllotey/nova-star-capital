from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Callable, Dict

from src.v2.portfolio.budget_context import load_budget_context


@dataclass(frozen=True)
class CapacityContract:
    max_positions: int
    max_new_entries_per_run: int
    max_total_notional_usd: float
    max_order_notional_usd: float | None
    max_buy_notional_usd_per_run: float | None = None
    max_buy_notional_usd_per_asset: float | None = None


@dataclass(frozen=True)
class BuyAdmission:
    allowed: bool
    reason: str
    is_new_position: bool
    projected_positions: int
    projected_notional_usd: float
    order_notional_usd: float


def _positive_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if not isfinite(out) or out <= 0:
        return None
    return out


def _positive_int(value: Any) -> int | None:
    try:
        out = int(value)
    except Exception:
        return None
    return out if out > 0 else None


def build_capacity_contract(
    *,
    governance: Dict[str, Any],
    scope: str = "equities_offensive",
    strategy_max_positions: int = 5,
    strategy_max_new_entries: int = 2,
    root: Path,
) -> CapacityContract:
    """
    Offensive BUY capacity authority.

    Portfolio pocket is the absolute economic ceiling.
    Governance/global risk and strategy may tighten authority,
    never widen the Portfolio budget.
    """
    root = Path(root)

    budget = load_budget_context(
        root,
        scope=scope,
    )

    if budget.get("status") != "ok":
        raise RuntimeError(
            "offensive_capacity_budget_invalid:"
            + str(budget.get("error") or "unknown")
        )

    budget_usd = _positive_float(
        budget.get("budget_usd")
    )
    if budget_usd is None:
        raise RuntimeError(
            "offensive_capacity_budget_non_positive"
        )

    gov = governance if isinstance(governance, dict) else {}

    inputs = gov.get("inputs")
    if not isinstance(inputs, dict):
        inputs = {}

    risk_limits = inputs.get("risk_limits")
    if not isinstance(risk_limits, dict):
        risk_limits = {}

    caps = gov.get("caps")
    if not isinstance(caps, dict):
        caps = {}

    position_limits = []

    global_max_positions = _positive_int(
        risk_limits.get("max_positions")
    )
    if global_max_positions is not None:
        position_limits.append(global_max_positions)

    local_max_positions = _positive_int(
        strategy_max_positions
    )
    if local_max_positions is not None:
        position_limits.append(local_max_positions)

    if not position_limits:
        raise RuntimeError(
            "offensive_capacity_max_positions_missing"
        )

    max_new_entries = _positive_int(
        strategy_max_new_entries
    )
    if max_new_entries is None:
        raise RuntimeError(
            "offensive_capacity_max_new_entries_invalid"
        )

    max_order_notional = _positive_float(
        caps.get("max_order_notional_usd")
    )

    fx = budget.get("fx")
    if not isinstance(fx, dict):
        raise RuntimeError(
            "offensive_capacity_fx_missing"
        )

    fx_pair = str(fx.get("pair") or "").upper()
    fx_rate = _positive_float(fx.get("rate"))

    if fx_pair != "EUR/USD" or fx_rate is None:
        raise RuntimeError(
            "offensive_capacity_fx_invalid"
        )

    def eur_cap_to_usd(name: str) -> float | None:
        raw = caps.get(name)

        if raw is None:
            return None

        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise RuntimeError(
                f"offensive_capacity_{name}_invalid"
            )

        if not isfinite(value):
            raise RuntimeError(
                f"offensive_capacity_{name}_invalid"
            )

        # Existing governance semantics:
        # zero means unlimited/not configured.
        if value <= 0:
            return None

        return value * fx_rate

    max_buy_notional_run = eur_cap_to_usd(
        "max_notional_eur_per_run"
    )
    max_buy_notional_asset = eur_cap_to_usd(
        "max_notional_eur_per_asset"
    )

    return CapacityContract(
        max_positions=min(position_limits),
        max_new_entries_per_run=max_new_entries,
        max_total_notional_usd=budget_usd,
        max_order_notional_usd=max_order_notional,
        max_buy_notional_usd_per_run=max_buy_notional_run,
        max_buy_notional_usd_per_asset=max_buy_notional_asset,
    )


def _position_values(position: Any) -> tuple[float, float]:
    if isinstance(position, dict):
        qty = position.get("qty", 0.0)
        avg_price = position.get("avg_price", 0.0)
    else:
        qty = getattr(position, "qty", 0.0)
        avg_price = getattr(position, "avg_price", 0.0)

    try:
        qty_f = float(qty or 0.0)
        avg_f = float(avg_price or 0.0)
    except Exception:
        return 0.0, 0.0

    return qty_f, avg_f


def admit_buy(
    *,
    contract: CapacityContract,
    positions: Dict[str, Any],
    symbol: str,
    qty: float,
    price: float,
    new_entries_used: int,
    buy_notional_used: float = 0.0,
    buy_notional_by_asset_used: float = 0.0,
    price_resolver: Callable[[str, float], float] | None = None,
) -> BuyAdmission:
    """
    Evaluate projected state before a BUY.

    Existing positions are valued at current order price only for
    the target symbol and at avg_price for other symbols. The
    Broker therefore remains the final authority using its current
    market fill price.

    Reinforcement consumes notional capacity but does not consume
    a new-position slot.
    """
    symbol = str(symbol or "").upper()

    try:
        qty = float(qty)
        price = float(price)
        new_entries_used = int(new_entries_used)
        buy_notional_used = float(buy_notional_used)
        buy_notional_by_asset_used = float(
            buy_notional_by_asset_used
        )
    except Exception:
        return BuyAdmission(
            False,
            "capacity_invalid_numeric_input",
            False,
            0,
            0.0,
            0.0,
        )

    if (
        not symbol
        or not isfinite(qty)
        or not isfinite(price)
        or qty <= 0
        or price <= 0
        or new_entries_used < 0
        or not isfinite(buy_notional_used)
        or buy_notional_used < 0
        or not isfinite(buy_notional_by_asset_used)
        or buy_notional_by_asset_used < 0
    ):
        return BuyAdmission(
            False,
            "capacity_invalid_numeric_input",
            False,
            0,
            0.0,
            0.0,
        )

    positions = positions if isinstance(positions, dict) else {}

    current_notional = 0.0
    open_positions = 0
    target_open = False

    for raw_symbol, position in positions.items():
        pos_symbol = str(raw_symbol or "").upper()
        pos_qty, avg_price = _position_values(position)

        if pos_qty <= 0:
            continue

        open_positions += 1

        if pos_symbol == symbol:
            target_open = True
            valuation_price = price
        elif price_resolver is not None:
            try:
                valuation_price = float(
                    price_resolver(pos_symbol, avg_price)
                )
            except Exception:
                valuation_price = 0.0
        else:
            valuation_price = avg_price

        if (
            not isfinite(valuation_price)
            or valuation_price <= 0
        ):
            return BuyAdmission(
                False,
                "capacity_existing_position_price_invalid",
                False,
                open_positions,
                current_notional,
                qty * price,
            )

        current_notional += pos_qty * valuation_price

    is_new = not target_open
    projected_positions = open_positions + (1 if is_new else 0)
    order_notional = qty * price
    projected_notional = current_notional + order_notional

    if (
        is_new
        and new_entries_used
        >= contract.max_new_entries_per_run
    ):
        return BuyAdmission(
            False,
            "max_new_entries_per_run",
            is_new,
            projected_positions,
            projected_notional,
            order_notional,
        )

    if projected_positions > contract.max_positions:
        return BuyAdmission(
            False,
            "max_positions",
            is_new,
            projected_positions,
            projected_notional,
            order_notional,
        )

    if (
        contract.max_order_notional_usd is not None
        and order_notional
        > contract.max_order_notional_usd
    ):
        return BuyAdmission(
            False,
            "max_order_notional_usd",
            is_new,
            projected_positions,
            projected_notional,
            order_notional,
        )

    if (
        contract.max_buy_notional_usd_per_run is not None
        and (
            buy_notional_used + order_notional
            > contract.max_buy_notional_usd_per_run
        )
    ):
        return BuyAdmission(
            False,
            "max_notional_eur_per_run",
            is_new,
            projected_positions,
            projected_notional,
            order_notional,
        )

    if (
        contract.max_buy_notional_usd_per_asset is not None
        and (
            buy_notional_by_asset_used + order_notional
            > contract.max_buy_notional_usd_per_asset
        )
    ):
        return BuyAdmission(
            False,
            "max_notional_eur_per_asset",
            is_new,
            projected_positions,
            projected_notional,
            order_notional,
        )

    if (
        projected_notional
        > contract.max_total_notional_usd
    ):
        return BuyAdmission(
            False,
            "portfolio_pocket_budget",
            is_new,
            projected_positions,
            projected_notional,
            order_notional,
        )

    return BuyAdmission(
        True,
        "allowed",
        is_new,
        projected_positions,
        projected_notional,
        order_notional,
    )
