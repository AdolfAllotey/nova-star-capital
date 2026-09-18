from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.v2.precious_metals.eur_pricing import build_eur_prices
from src.v2.market.preprod_price_contract import (
    load_fresh_prices,
)


ROOT = Path(
    os.getenv(
        "NSC_DATA_DIR",
        "/opt/nsc/data/preprod",
    )
)

SIGNAL_PATH = ROOT / "metals/metals_signal.json"
PRICES_PATH = ROOT / "metals/prices.json"

FILLS_PATH = (
    ROOT
    / "metals/execution/simulated_fills.jsonl"
)
POSITIONS_PATH = (
    ROOT
    / "metals/state/positions.json"
)
EXPOSURE_PATH = (
    ROOT
    / "metals/state/exposure_snapshot.json"
)

PORTFOLIO_STATE_PATH = (
    ROOT
    / "portfolio/state/portfolio_state.json"
)
GOVERNANCE_PATH = (
    ROOT
    / "analysis/governance_engine_pro.json"
)

EXPECTED_PRICE_SYMBOLS = (
    "GLD",
    "SLV",
)

MAX_PRICE_AGE_SECONDS = 6 * 60 * 60

SAFE_PREPROD_POLICIES = {
    "SIMULATED_ONLY",
    "SIMULATED_EXECUTION",
    "EXIT_ONLY",
}

EPSILON_QTY = 1e-9


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_json(
    path: Path,
    default=None,
):
    try:
        if path.exists():
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
    except Exception:
        pass

    return default


def save_json(
    path: Path,
    payload,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def append_jsonl(
    path: Path,
    row: dict,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                row,
                ensure_ascii=False,
            )
            + "\n"
        )


def load_positions() -> Dict[
    str,
    Dict[str, float],
]:
    doc = load_json(
        POSITIONS_PATH,
        default={},
    ) or {}

    if not isinstance(doc, dict):
        raise RuntimeError(
            "metals positions state must "
            "be a JSON object"
        )

    return doc


def save_positions(doc):
    save_json(
        POSITIONS_PATH,
        doc,
    )


def governance_contract() -> Dict[
    str,
    Any,
]:
    governance = load_json(
        GOVERNANCE_PATH,
        default=None,
    )

    if not isinstance(
        governance,
        dict,
    ):
        raise RuntimeError(
            "metals governance artifact "
            "missing or invalid"
        )

    env = str(
        governance.get("env") or ""
    ).upper()

    policy = str(
        governance.get(
            "action_policy"
        )
        or ""
    ).upper()

    hard_block = bool(
        governance.get(
            "hard_block",
            False,
        )
    )

    caps = (
        governance.get("caps")
        or {}
    )

    if env != "PREPROD":
        raise RuntimeError(
            "metals simulated broker "
            f"requires PREPROD, got {env!r}"
        )

    if (
        policy
        not in SAFE_PREPROD_POLICIES
    ):
        raise RuntimeError(
            "unsafe metals PREPROD "
            f"action_policy={policy!r}"
        )

    return {
        "env": env,
        "policy": policy,
        "hard_block": hard_block,
        "caps": (
            caps
            if isinstance(caps, dict)
            else {}
        ),
    }


def build_exposure_snapshot(
    positions: Dict[
        str,
        Dict[str, float],
    ],
    prices: Dict[str, float],
    *,
    action_policy: str,
    hard_block: bool,
):
    total = 0.0
    lines = []

    for sym, row in sorted(
        positions.items()
    ):
        qty = float(
            row.get("qty", 0.0)
            or 0.0
        )
        avg = float(
            row.get("avg_price", 0.0)
            or 0.0
        )
        px = float(
            prices.get(sym, 0.0)
            or 0.0
        )

        if qty <= 0:
            continue

        if px <= 0:
            raise RuntimeError(
                "missing valid metals mark "
                f"price for {sym}"
            )

        notional = round(
            qty * px,
            2,
        )

        total += notional

        lines.append({
            "symbol": sym,
            "qty": qty,
            "avg_price": avg,
            "price": px,
            "notional_eur": notional,
            "unrealized_pnl_eur": round(
                (px - avg) * qty,
                2,
            ),
        })

    snap = {
        "ts": now_iso(),
        "engine":
            "metals_simulated_broker_v2",
        "env": "PREPROD",
        "execution_mode":
            action_policy,
        "hard_block": hard_block,
        "open_positions": len(lines),
        "total_notional_eur": round(
            total,
            2,
        ),
        "positions": lines,
    }

    save_json(
        EXPOSURE_PATH,
        snap,
    )

    return snap


def _target_positions(
    signal: dict,
    prices: Dict[str, float],
    target_amount_eur: float,
) -> Dict[str, Dict[str, Any]]:
    allocation = (
        signal.get("allocation")
        or {}
    )

    if not isinstance(
        allocation,
        dict,
    ):
        raise RuntimeError(
            "metals allocation must "
            "be a dict"
        )

    targets: Dict[
        str,
        Dict[str, Any],
    ] = {}

    if target_amount_eur <= 0:
        return targets

    for raw_symbol, raw_weight in (
        allocation.items()
    ):
        sym = str(
            raw_symbol or ""
        ).strip().upper()

        if not sym:
            continue

        weight = float(
            raw_weight or 0.0
        )

        if weight <= 0:
            continue

        px = float(
            prices.get(sym, 0.0)
            or 0.0
        )

        if px <= 0:
            raise RuntimeError(
                "missing valid metals "
                f"execution price for {sym}"
            )

        amount = (
            target_amount_eur
            * weight
        )

        qty = round(
            amount / px,
            8,
        )

        if qty <= 0:
            continue

        targets[sym] = {
            "qty": qty,
            "price": px,
            "weight": weight,
        }

    return targets


def _apply_rebalance_deadband(
    current: Dict[
        str,
        Dict[str, float],
    ],
    targets: Dict[
        str,
        Dict[str, Any],
    ],
    prices: Dict[str, float],
    threshold: float,
) -> Dict[str, Dict[str, Any]]:
    threshold = max(
        float(threshold or 0.0),
        0.0,
    )

    effective = {
        symbol: dict(row)
        for symbol, row
        in targets.items()
    }

    if threshold <= 0:
        return effective

    for symbol in sorted(
        set(current)
        & set(targets)
    ):
        prev_qty = float(
            (
                current.get(symbol)
                or {}
            ).get(
                "qty",
                0.0,
            )
            or 0.0
        )

        target_qty = float(
            (
                targets.get(symbol)
                or {}
            ).get(
                "qty",
                0.0,
            )
            or 0.0
        )

        if prev_qty <= EPSILON_QTY:
            continue

        if target_qty <= EPSILON_QTY:
            continue

        px = float(
            prices.get(
                symbol,
                0.0,
            )
            or 0.0
        )

        if px <= 0:
            raise RuntimeError(
                "missing metals deadband "
                f"price for {symbol}"
            )

        current_notional = (
            prev_qty * px
        )
        target_notional = (
            target_qty * px
        )

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
            effective[
                symbol
            ]["qty"] = prev_qty

            effective[
                symbol
            ][
                "rebalance_suppressed"
            ] = True

            effective[
                symbol
            ][
                "rebalance_drift_ratio"
            ] = round(
                drift_ratio,
                8,
            )

    return effective


def _validate_caps(
    current: Dict[
        str,
        Dict[str, float],
    ],
    targets: Dict[
        str,
        Dict[str, Any],
    ],
    prices: Dict[str, float],
    caps: Dict[str, Any],
) -> None:
    max_asset = float(
        caps.get(
            "max_notional_eur_per_asset",
            0.0,
        )
        or 0.0
    )

    max_run = float(
        caps.get(
            "max_notional_eur_per_run",
            0.0,
        )
        or 0.0
    )

    max_orders = int(
        caps.get(
            "max_orders_per_run",
            0,
        )
        or 0
    )

    order_count = 0
    changed_notional = 0.0

    for sym in sorted(
        set(current)
        | set(targets)
    ):
        prev_qty = float(
            (
                current.get(sym)
                or {}
            ).get(
                "qty",
                0.0,
            )
            or 0.0
        )

        target = (
            targets.get(sym)
            or {}
        )

        target_qty = float(
            target.get(
                "qty",
                0.0,
            )
            or 0.0
        )

        px = float(
            prices.get(
                sym,
                target.get(
                    "price",
                    (
                        current.get(sym)
                        or {}
                    ).get(
                        "avg_price",
                        0.0,
                    ),
                ),
            )
            or 0.0
        )

        if (
            target_qty > 0
            and max_asset > 0
        ):
            target_notional = (
                target_qty * px
            )

            if (
                target_notional
                > max_asset + 1e-6
            ):
                raise RuntimeError(
                    f"metals target {sym} "
                    "notional "
                    f"{target_notional:.2f} "
                    "exceeds per-asset cap "
                    f"{max_asset:.2f}"
                )

        delta_qty = abs(
            target_qty - prev_qty
        )

        if delta_qty > EPSILON_QTY:
            order_count += 1
            changed_notional += (
                delta_qty * px
            )

    # PREPROD convention:
    # max_orders_per_run == 0
    # means unlimited.
    if (
        max_orders > 0
        and order_count > max_orders
    ):
        raise RuntimeError(
            "metals order count "
            f"{order_count} exceeds "
            f"cap {max_orders}"
        )

    if (
        max_run > 0
        and changed_notional
        > max_run + 1e-6
    ):
        raise RuntimeError(
            "metals changed notional "
            f"{changed_notional:.2f} "
            "exceeds run cap "
            f"{max_run:.2f}"
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
            "engine":
                "metals_simulated_broker_v2",
            "env": "PREPROD",
            "execution_mode":
                action_policy,
            "symbol": symbol,
            "side": side,
            "qty": round(
                qty,
                8,
            ),
            "fill_price": round(
                price,
                8,
            ),
            "fill_price_eur": round(
                price,
                8,
            ),
            "avg_price_before": round(
                avg_price_before,
                8,
            ),
            "avg_price_before_eur":
                round(
                    avg_price_before,
                    8,
                ),
            "native_price": round(
                pricing.native_price,
                8,
            ),
            "native_currency":
                pricing.native_currency,
            "yahoo_symbol":
                pricing.yahoo_symbol,
            "fx_to_eur": round(
                pricing.fx_to_eur,
                12,
            ),
            "fx_pair":
                pricing.fx.get("pair"),
            "fx_provider":
                pricing.fx.get(
                    "provider"
                ),
            "fx_market_timestamp":
                pricing.fx.get(
                    "market_timestamp"
                ),
            "realized_pnl_eur":
                round(
                    realized_pnl_eur,
                    8,
                ),
            "status": "FILLED",
            "portfolio_regime":
                portfolio_regime,
            "reason": reason,
        },
    )


def main():
    signal = load_json(
        SIGNAL_PATH,
        default=None,
    )

    portfolio_state = load_json(
        PORTFOLIO_STATE_PATH,
        default=None,
    )

    if not isinstance(
        signal,
        dict,
    ):
        raise RuntimeError(
            "metals signal missing "
            "or invalid"
        )

    if not isinstance(
        portfolio_state,
        dict,
    ):
        raise RuntimeError(
            "portfolio state missing "
            "or invalid"
        )

    native_prices = (
        load_fresh_prices(
            sleeve="metals",
            prices_path=PRICES_PATH,
            expected_symbols=
                EXPECTED_PRICE_SYMBOLS,
            max_age_seconds=
                MAX_PRICE_AGE_SECONDS,
        ).prices
    )

    eur_pricing = build_eur_prices(
        native_prices
    )

    prices = {
        symbol: row.price_eur
        for symbol, row
        in eur_pricing.items()
    }

    current = load_positions()

    governance = (
        governance_contract()
    )

    action_policy = (
        governance["policy"]
    )
    hard_block = (
        governance["hard_block"]
    )
    caps = governance["caps"]

    portfolio_regime = str(
        portfolio_state.get(
            "portfolio_regime"
        )
        or "unknown"
    ).lower()

    metals = (
        (
            portfolio_state.get(
                "bricks"
            )
            or {}
        ).get(
            "precious_metals",
            {},
        )
        or {}
    )

    governed_target = bool(
        metals.get(
            "governed_target",
            False,
        )
    )

    target_amount = float(
        metals.get(
            "target_amount_eur",
            0.0,
        )
        or 0.0
    )

    inertia_profile = (
        metals.get(
            "inertia_profile"
        )
        or {}
    )

    min_rebalance_threshold = float(
        inertia_profile.get(
            "min_threshold_to_rebalance",
            0.0,
        )
        or 0.0
    )

    if (
        not governed_target
        and target_amount > 0
    ):
        raise RuntimeError(
            "metals target amount is "
            "non-zero without "
            "governed_target=true"
        )

    targets = _target_positions(
        signal,
        prices,
        (
            target_amount
            if governed_target
            else 0.0
        ),
    )

    if action_policy == "EXIT_ONLY":
        for sym, target in list(
            targets.items()
        ):
            prev_qty = float(
                (
                    current.get(sym)
                    or {}
                ).get(
                    "qty",
                    0.0,
                )
                or 0.0
            )

            target["qty"] = min(
                float(
                    target.get(
                        "qty",
                        0.0,
                    )
                    or 0.0
                ),
                prev_qty,
            )

            if (
                target["qty"]
                <= EPSILON_QTY
            ):
                targets.pop(
                    sym,
                    None,
                )

    targets = (
        _apply_rebalance_deadband(
            current,
            targets,
            prices,
            min_rebalance_threshold,
        )
    )

    _validate_caps(
        current,
        targets,
        prices,
        caps,
    )

    if hard_block:
        snap = (
            build_exposure_snapshot(
                current,
                prices,
                action_policy=
                    action_policy,
                hard_block=True,
            )
        )

        result = {
            "status": "blocked",
            "engine":
                "metals_simulated_broker_v2",
            "reason":
                "governance_hard_block",
            "portfolio_regime":
                portfolio_regime,
            "target_amount_eur":
                round(
                    target_amount,
                    2,
                ),
            "positions_written":
                len(current),
            "fills_written": 0,
            "snapshot": snap,
        }

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

        return result

    new_positions: Dict[
        str,
        Dict[str, float],
    ] = {}

    fills_written = 0

    for sym in sorted(
        set(current)
        | set(targets)
    ):
        prev = (
            current.get(sym)
            or {}
        )
        target = (
            targets.get(sym)
            or {}
        )

        prev_qty = float(
            prev.get(
                "qty",
                0.0,
            )
            or 0.0
        )

        prev_avg = float(
            prev.get(
                "avg_price",
                0.0,
            )
            or 0.0
        )

        target_qty = float(
            target.get(
                "qty",
                0.0,
            )
            or 0.0
        )

        px = float(
            prices.get(
                sym,
                target.get(
                    "price",
                    0.0,
                ),
            )
            or 0.0
        )

        if (
            prev_qty > 0
            and prev_avg <= 0
        ):
            raise RuntimeError(
                "invalid avg_price for "
                "existing metals position "
                f"{sym}"
            )

        if (
            abs(
                target_qty
                - prev_qty
            )
            > EPSILON_QTY
            and px <= 0
        ):
            raise RuntimeError(
                "missing execution price "
                "for metals rebalance "
                f"{sym}"
            )

        # BUY / reinforcement.
        if (
            target_qty
            > prev_qty
            + EPSILON_QTY
        ):
            buy_qty = (
                target_qty
                - prev_qty
            )

            if (
                action_policy
                == "EXIT_ONLY"
            ):
                target_qty = (
                    prev_qty
                )
            else:
                if prev_qty > 0:
                    new_avg = (
                        (
                            prev_qty
                            * prev_avg
                        )
                        + (
                            buy_qty
                            * px
                        )
                    ) / target_qty
                else:
                    new_avg = px

                _fill(
                    symbol=sym,
                    side="BUY",
                    qty=buy_qty,
                    price=px,
                    avg_price_before=
                        prev_avg,
                    realized_pnl_eur=0.0,
                    action_policy=
                        action_policy,
                    portfolio_regime=
                        portfolio_regime,
                    reason=
                        "governed_target_rebalance",
                    pricing=
                        eur_pricing[sym],
                )

                fills_written += 1

                new_positions[sym] = {
                    "qty": round(
                        target_qty,
                        8,
                    ),
                    "avg_price": round(
                        new_avg,
                        8,
                    ),
                }

                continue

        # SELL / removal.
        if (
            target_qty
            < prev_qty
            - EPSILON_QTY
        ):
            sell_qty = (
                prev_qty
                - target_qty
            )

            realized = (
                px - prev_avg
            ) * sell_qty

            _fill(
                symbol=sym,
                side="SELL",
                qty=sell_qty,
                price=px,
                avg_price_before=
                    prev_avg,
                realized_pnl_eur=
                    realized,
                action_policy=
                    action_policy,
                portfolio_regime=
                    portfolio_regime,
                reason=(
                    "removed_from_governed_target"
                    if sym not in targets
                    else
                    "governed_target_rebalance"
                ),
                pricing=
                    eur_pricing[sym],
            )

            fills_written += 1

            if (
                target_qty
                > EPSILON_QTY
            ):
                new_positions[sym] = {
                    "qty": round(
                        target_qty,
                        8,
                    ),
                    "avg_price": round(
                        prev_avg,
                        8,
                    ),
                }

            continue

        # Unchanged / deadbanded.
        if (
            prev_qty
            > EPSILON_QTY
        ):
            new_positions[sym] = {
                "qty": round(
                    prev_qty,
                    8,
                ),
                "avg_price": round(
                    prev_avg,
                    8,
                ),
            }

    save_positions(
        new_positions
    )

    snap = (
        build_exposure_snapshot(
            new_positions,
            prices,
            action_policy=
                action_policy,
            hard_block=False,
        )
    )

    result = {
        "status": "ok",
        "engine":
            "metals_simulated_broker_v2",
        "env": "PREPROD",
        "execution_mode":
            action_policy,
        "portfolio_regime":
            portfolio_regime,
        "governed_target":
            governed_target,
        "target_amount_eur":
            round(
                target_amount,
                2,
            ),
        "min_rebalance_threshold":
            round(
                min_rebalance_threshold,
                6,
            ),
        "positions_written":
            len(new_positions),
        "fills_written":
            fills_written,
        "snapshot": snap,
    }

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return result


if __name__ == "__main__":
    main()
