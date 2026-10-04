from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.v2.utils.file_utils import get_data_dir
from types import SimpleNamespace
from typing import Any, Dict

from src.v2.market.preprod_price_contract import load_fresh_prices
from src.v2.defensive_equities.common import load_defensive_universe
from src.v2.defensive_equities.eur_pricing import build_eur_prices


ROOT = get_data_dir()

SIGNAL_PATH = ROOT / "defensive/defensive_signal.json"
PRICES_PATH = ROOT / "defensive/prices.json"
MAX_PRICE_AGE_SECONDS = 6 * 60 * 60

FILLS_PATH = ROOT / "defensive/execution/simulated_fills.jsonl"
POSITIONS_PATH = ROOT / "defensive/state/positions.json"
EXPOSURE_PATH = ROOT / "defensive/state/exposure_snapshot.json"

PORTFOLIO_STATE_PATH = ROOT / "portfolio/state/portfolio_state.json"
GOVERNANCE_PATH = ROOT / "analysis/governance_engine_pro.json"

SAFE_PREPROD_POLICIES = {
    "SIMULATED_ONLY",
    "SIMULATED_EXECUTION",
    "EXIT_ONLY",
}

EPSILON_QTY = 1e-9


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_positions() -> Dict[str, Dict[str, float]]:
    doc = load_json(POSITIONS_PATH, default={}) or {}
    if not isinstance(doc, dict):
        raise RuntimeError("defensive positions state must be a JSON object")
    return doc


def save_positions(doc):
    save_json(POSITIONS_PATH, doc)


def governance_contract() -> Dict[str, Any]:
    governance = load_json(GOVERNANCE_PATH, default=None)

    if not isinstance(governance, dict):
        raise RuntimeError("defensive governance artifact missing or invalid")

    env = str(governance.get("env") or "").upper()
    policy = str(
        governance.get("action_policy") or ""
    ).upper()
    hard_block = bool(governance.get("hard_block", False))
    caps = governance.get("caps") or {}

    if env != "PREPROD":
        raise RuntimeError(
            f"defensive simulated broker requires PREPROD governance, got {env!r}"
        )

    if policy not in SAFE_PREPROD_POLICIES:
        raise RuntimeError(
            f"unsafe defensive PREPROD action_policy={policy!r}"
        )

    return {
        "env": env,
        "policy": policy,
        "hard_block": hard_block,
        "caps": caps if isinstance(caps, dict) else {},
    }


def build_exposure_snapshot(
    positions: Dict[str, Dict[str, float]],
    prices: Dict[str, float],
    *,
    action_policy: str,
    hard_block: bool,
):
    total = 0.0
    lines = []

    for sym, row in sorted(positions.items()):
        qty = float(row.get("qty", 0.0) or 0.0)
        avg = float(row.get("avg_price", 0.0) or 0.0)
        px = float(prices.get(sym, 0.0) or 0.0)

        if qty <= 0:
            continue
        if px <= 0:
            raise RuntimeError(
                f"missing valid mark price for open defensive position {sym}"
            )

        notional = round(qty * px, 2)
        total += notional

        lines.append({
            "symbol": sym,
            "qty": qty,
            "avg_price": avg,
            "price": px,
            "notional_eur": notional,
            "unrealized_pnl_eur": round((px - avg) * qty, 2),
        })

    snap = {
        "ts": now_iso(),
        "engine": "defensive_simulated_broker_v2",
        "env": "PREPROD",
        "execution_mode": action_policy,
        "hard_block": hard_block,
        "open_positions": len(lines),
        "total_notional_eur": round(total, 2),
        "positions": lines,
    }

    save_json(EXPOSURE_PATH, snap)
    return snap


def _target_positions(
    signal: dict,
    prices: Dict[str, float],
    target_amount_eur: float,
) -> Dict[str, Dict[str, Any]]:
    proposed_assets = signal.get("proposed_assets") or []

    if not isinstance(proposed_assets, list):
        raise RuntimeError("defensive proposed_assets must be a list")

    targets: Dict[str, Dict[str, Any]] = {}

    if target_amount_eur <= 0:
        return targets

    for asset in proposed_assets:
        if not isinstance(asset, dict):
            continue

        sym = str(asset.get("ticker") or "").strip().upper()
        if not sym:
            continue

        weight = float(asset.get("weight", 0.0) or 0.0)
        px = float(prices.get(sym, 0.0) or 0.0)

        if weight <= 0:
            continue

        if px <= 0:
            raise RuntimeError(
                f"missing valid defensive execution price for {sym}"
            )

        amount = target_amount_eur * weight
        qty = round(amount / px, 8)

        if qty <= 0:
            continue

        targets[sym] = {
            "qty": qty,
            "price": px,
            "weight": weight,
        }

    return targets


def _apply_rebalance_deadband(
    current: Dict[str, Dict[str, float]],
    targets: Dict[str, Dict[str, Any]],
    prices: Dict[str, float],
    threshold: float,
) -> Dict[str, Dict[str, Any]]:
    """
    Preserve existing quantities when per-position notional drift
    remains below the Portfolio inertia threshold.

    New positions and complete exits are never suppressed.
    """
    threshold = max(float(threshold or 0.0), 0.0)

    effective = {
        symbol: dict(row)
        for symbol, row in targets.items()
    }

    if threshold <= 0:
        return effective

    for symbol in sorted(set(current) & set(targets)):
        prev_qty = float(
            (current.get(symbol) or {}).get(
                "qty",
                0.0,
            )
            or 0.0
        )
        target_qty = float(
            (targets.get(symbol) or {}).get(
                "qty",
                0.0,
            )
            or 0.0
        )
        px = float(
            prices.get(symbol, 0.0) or 0.0
        )

        # New entries / exits are not deadbanded.
        if prev_qty <= EPSILON_QTY:
            continue
        if target_qty <= EPSILON_QTY:
            continue

        if px <= 0:
            raise RuntimeError(
                f"missing defensive deadband price "
                f"for {symbol}"
            )

        current_notional = prev_qty * px
        target_notional = target_qty * px

        if target_notional <= 0:
            continue

        drift_ratio = (
            abs(
                target_notional
                - current_notional
            )
            / target_notional
        )

        if drift_ratio < threshold:
            effective[symbol]["qty"] = prev_qty
            effective[symbol][
                "rebalance_suppressed"
            ] = True
            effective[symbol][
                "rebalance_drift_ratio"
            ] = round(drift_ratio, 8)

    return effective


def _validate_caps(
    current: Dict[str, Dict[str, float]],
    targets: Dict[str, Dict[str, Any]],
    prices: Dict[str, float],
    caps: Dict[str, Any],
) -> None:
    max_asset = float(
        caps.get("max_notional_eur_per_asset", 0.0) or 0.0
    )
    max_run = float(
        caps.get("max_notional_eur_per_run", 0.0) or 0.0
    )
    max_orders = int(
        caps.get("max_orders_per_run", 0) or 0
    )

    order_count = 0
    changed_notional = 0.0

    for sym in sorted(set(current) | set(targets)):
        prev_qty = float(
            (current.get(sym) or {}).get("qty", 0.0) or 0.0
        )
        target = targets.get(sym) or {}
        target_qty = float(target.get("qty", 0.0) or 0.0)

        px = float(
            prices.get(
                sym,
                target.get(
                    "price",
                    (current.get(sym) or {}).get("avg_price", 0.0),
                ),
            )
            or 0.0
        )

        if target_qty > 0 and max_asset > 0:
            target_notional = target_qty * px
            if target_notional > max_asset + 1e-6:
                raise RuntimeError(
                    f"defensive target {sym} notional "
                    f"{target_notional:.2f} exceeds per-asset cap "
                    f"{max_asset:.2f}"
                )

        delta_qty = abs(target_qty - prev_qty)
        if delta_qty > EPSILON_QTY:
            order_count += 1
            changed_notional += delta_qty * px

    # PREPROD contract: zero means unlimited order count.
    if max_orders > 0 and order_count > max_orders:
        raise RuntimeError(
            f"defensive order count {order_count} exceeds cap {max_orders}"
        )

    if max_run > 0 and changed_notional > max_run + 1e-6:
        raise RuntimeError(
            f"defensive changed notional {changed_notional:.2f} "
            f"exceeds run cap {max_run:.2f}"
        )


def _fill(
    *,
    symbol: str,
    side: str,
    qty: float,
    price: float,
    avg_price_before: float,
    realized_pnl_eur: float,
    action_policy: str,
    portfolio_regime: str,
    reason: str,
    pricing,
):
    append_jsonl(
        FILLS_PATH,
        {
            "ts": now_iso(),
            "engine": "defensive_simulated_broker_v2",
            "env": "PREPROD",
            "execution_mode": action_policy,
            "symbol": symbol,
            "side": side,
            "qty": round(qty, 8),
            # Canonical accounting price is EUR.
            "fill_price": round(price, 8),
            "fill_price_eur": round(price, 8),
            "avg_price_before": round(avg_price_before, 8),
            "avg_price_before_eur": round(avg_price_before, 8),

            # Native market-price provenance.
            "native_price": round(pricing.native_price, 8),
            "native_currency": pricing.native_currency,
            "yahoo_symbol": pricing.yahoo_symbol,
            "fx_to_eur": round(pricing.fx_to_eur, 12),
            "fx_pair": pricing.fx.get("pair"),
            "fx_provider": pricing.fx.get("provider"),
            "fx_market_timestamp": pricing.fx.get(
                "market_timestamp"
            ),

            "realized_pnl_eur": round(realized_pnl_eur, 8),
            "status": "FILLED",
            "portfolio_regime": portfolio_regime,
            "reason": reason,
        },
    )


def main():
    signal = load_json(SIGNAL_PATH, default=None)
    portfolio_state = load_json(PORTFOLIO_STATE_PATH, default=None)

    if not isinstance(signal, dict):
        raise RuntimeError("defensive signal missing or invalid")

    if not isinstance(portfolio_state, dict):
        raise RuntimeError("portfolio state missing or invalid")

    native_prices = load_fresh_prices(
        sleeve="defensive",
        prices_path=PRICES_PATH,
        expected_symbols=load_defensive_universe(),
        max_age_seconds=MAX_PRICE_AGE_SECONDS,
    ).prices

    eur_pricing = build_eur_prices(native_prices)

    prices = {
        symbol: row.price_eur
        for symbol, row in eur_pricing.items()
    }

    current = load_positions()
    governance = governance_contract()

    action_policy = governance["policy"]
    hard_block = governance["hard_block"]
    caps = governance["caps"]

    portfolio_regime = str(
        portfolio_state.get("portfolio_regime") or "unknown"
    ).lower()

    defensive = (
        (portfolio_state.get("bricks") or {})
        .get("equities_defensive", {})
        or {}
    )

    governed_target = bool(
        defensive.get("governed_target", False)
    )
    target_amount = float(
        defensive.get("target_amount_eur", 0.0) or 0.0
    )

    inertia_profile = (
        defensive.get("inertia_profile") or {}
    )

    min_rebalance_threshold = float(
        inertia_profile.get(
            "min_threshold_to_rebalance",
            0.0,
        )
        or 0.0
    )

    if not governed_target and target_amount > 0:
        raise RuntimeError(
            "defensive target amount is non-zero without governed_target=true"
        )

    targets = _target_positions(
        signal,
        prices,
        target_amount if governed_target else 0.0,
    )

    # EXIT_ONLY can preserve/reduce existing positions but must never
    # create or increase exposure.
    if action_policy == "EXIT_ONLY":
        for sym, target in list(targets.items()):
            prev_qty = float(
                (current.get(sym) or {}).get("qty", 0.0) or 0.0
            )
            target["qty"] = min(
                float(target.get("qty", 0.0) or 0.0),
                prev_qty,
            )
            if target["qty"] <= 0:
                targets.pop(sym, None)

    targets = _apply_rebalance_deadband(
        current,
        targets,
        prices,
        min_rebalance_threshold,
    )

    _validate_caps(
        current,
        targets,
        prices,
        caps,
    )

    if hard_block:
        snap = build_exposure_snapshot(
            current,
            prices,
            action_policy=action_policy,
            hard_block=True,
        )

        result = {
            "status": "blocked",
            "engine": "defensive_simulated_broker_v2",
            "reason": "governance_hard_block",
            "portfolio_regime": portfolio_regime,
            "target_amount_eur": target_amount,
            "positions_written": len(current),
            "fills_written": 0,
            "snapshot": snap,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    new_positions: Dict[str, Dict[str, float]] = {}
    fills_written = 0

    for sym in sorted(set(current) | set(targets)):
        prev = current.get(sym) or {}
        target = targets.get(sym) or {}

        prev_qty = float(prev.get("qty", 0.0) or 0.0)
        prev_avg = float(prev.get("avg_price", 0.0) or 0.0)

        target_qty = float(target.get("qty", 0.0) or 0.0)

        px = float(
            prices.get(
                sym,
                target.get("price", 0.0),
            )
            or 0.0
        )

        if prev_qty > 0 and prev_avg <= 0:
            raise RuntimeError(
                f"invalid avg_price for existing defensive position {sym}"
            )

        if (
            abs(target_qty - prev_qty) > EPSILON_QTY
            and px <= 0
        ):
            raise RuntimeError(
                f"missing execution price for defensive rebalance {sym}"
            )

        # Increase / new BUY.
        if target_qty > prev_qty + EPSILON_QTY:
            buy_qty = target_qty - prev_qty

            if action_policy == "EXIT_ONLY":
                target_qty = prev_qty
            else:
                if prev_qty > 0:
                    new_avg = (
                        (prev_qty * prev_avg)
                        + (buy_qty * px)
                    ) / target_qty
                else:
                    new_avg = px

                _fill(
                    symbol=sym,
                    side="BUY",
                    qty=buy_qty,
                    price=px,
                    avg_price_before=prev_avg,
                    realized_pnl_eur=0.0,
                    action_policy=action_policy,
                    portfolio_regime=portfolio_regime,
                    reason="governed_target_rebalance",
                    pricing=eur_pricing[sym],
                )
                fills_written += 1

                new_positions[sym] = {
                    "qty": round(target_qty, 8),
                    "avg_price": round(new_avg, 8),
                }
                continue

        # Reduction / complete SELL, including symbols removed
        # from the target allocation.
        if target_qty < prev_qty - EPSILON_QTY:
            sell_qty = prev_qty - target_qty
            realized = (px - prev_avg) * sell_qty

            _fill(
                symbol=sym,
                side="SELL",
                qty=sell_qty,
                price=px,
                avg_price_before=prev_avg,
                realized_pnl_eur=realized,
                action_policy=action_policy,
                portfolio_regime=portfolio_regime,
                reason=(
                    "removed_from_governed_target"
                    if sym not in targets
                    else "governed_target_rebalance"
                ),
                pricing=eur_pricing[sym],
            )
            fills_written += 1

            if target_qty > EPSILON_QTY:
                new_positions[sym] = {
                    "qty": round(target_qty, 8),
                    "avg_price": round(prev_avg, 8),
                }
            continue

        # Unchanged open position.
        if prev_qty > EPSILON_QTY:
            new_positions[sym] = {
                "qty": round(prev_qty, 8),
                "avg_price": round(prev_avg, 8),
            }

    save_positions(new_positions)

    snap = build_exposure_snapshot(
        new_positions,
        prices,
        action_policy=action_policy,
        hard_block=False,
    )

    result = {
        "status": "ok",
        "engine": "defensive_simulated_broker_v2",
        "env": "PREPROD",
        "execution_mode": action_policy,
        "portfolio_regime": portfolio_regime,
        "governed_target": governed_target,
        "target_amount_eur": round(target_amount, 2),
        "min_rebalance_threshold": round(
            min_rebalance_threshold,
            6,
        ),
        "positions_written": len(new_positions),
        "fills_written": fills_written,
        "snapshot": snap,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
