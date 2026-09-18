from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
PORTFOLIO_STATE_PATH = (
    ROOT
    / "portfolio/state/portfolio_state.json"
)

PRICES_PATH = ROOT / "metals/prices.json"

POSITIONS_PATH = (
    ROOT
    / "metals/state/positions.json"
)
FILLS_PATH = (
    ROOT
    / "metals/execution/simulated_fills.jsonl"
)
EXPOSURE_PATH = (
    ROOT
    / "metals/state/exposure_snapshot.json"
)

OUT_PATH = ROOT / "metals/metals_state.json"

EXPECTED_PRICE_SYMBOLS = (
    "GLD",
    "SLV",
)

MAX_PRICE_AGE_SECONDS = 6 * 60 * 60


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


def load_jsonl(
    path: Path,
) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: List[
        Dict[str, Any]
    ] = []

    for line_no, line in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            row = json.loads(line)
        except Exception as exc:
            raise RuntimeError(
                "invalid metals fill JSON "
                f"at line {line_no}: {exc}"
            ) from exc

        if not isinstance(
            row,
            dict,
        ):
            raise RuntimeError(
                "invalid metals fill "
                f"at line {line_no}: "
                "expected object"
            )

        rows.append(row)

    return rows


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


def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def realized_pnl_from_fills(
    fills: List[
        Dict[str, Any]
    ],
) -> float:
    total = 0.0

    for row in fills:
        if (
            str(
                row.get("status")
                or ""
            ).upper()
            != "FILLED"
        ):
            continue

        if (
            str(
                row.get("side")
                or ""
            ).upper()
            != "SELL"
        ):
            continue

        try:
            total += float(
                row.get(
                    "realized_pnl_eur",
                    0.0,
                )
                or 0.0
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise RuntimeError(
                "invalid "
                "realized_pnl_eur "
                "in metals fills"
            ) from exc

    return round(
        total,
        8,
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
    broker_positions = load_json(
        POSITIONS_PATH,
        default=None,
    )
    exposure_snapshot = load_json(
        EXPOSURE_PATH,
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

    if not isinstance(
        broker_positions,
        dict,
    ):
        raise RuntimeError(
            "metals broker positions "
            "missing or invalid; "
            "state updater refuses "
            "synthetic reconstruction"
        )

    if not isinstance(
        exposure_snapshot,
        dict,
    ):
        raise RuntimeError(
            "metals broker exposure "
            "snapshot missing or invalid"
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

    fills = load_jsonl(
        FILLS_PATH
    )

    realized_pnl = (
        realized_pnl_from_fills(
            fills
        )
    )

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

    target_amount = float(
        metals.get(
            "target_amount_eur",
            0.0,
        )
        or 0.0
    )

    allocation = (
        signal.get("allocation")
        or {}
    )

    if not isinstance(
        allocation,
        dict,
    ):
        raise RuntimeError(
            "metals allocation "
            "must be a dict"
        )

    positions = []
    total_value = 0.0
    total_cost_basis = 0.0
    total_unrealized = 0.0

    for symbol, row in sorted(
        broker_positions.items()
    ):
        if not isinstance(
            row,
            dict,
        ):
            raise RuntimeError(
                "invalid metals broker "
                f"position for {symbol}"
            )

        qty = float(
            row.get(
                "qty",
                0.0,
            )
            or 0.0
        )

        avg_price = float(
            row.get(
                "avg_price",
                0.0,
            )
            or 0.0
        )

        if qty <= 0:
            continue

        if avg_price <= 0:
            raise RuntimeError(
                "invalid metals avg_price "
                f"for {symbol}"
            )

        px = float(
            prices.get(
                symbol,
                0.0,
            )
            or 0.0
        )

        if px <= 0:
            raise RuntimeError(
                "missing valid metals "
                f"mark price for {symbol}"
            )

        pricing = (
            eur_pricing.get(symbol)
        )

        if pricing is None:
            raise RuntimeError(
                "missing metals EUR "
                f"pricing for {symbol}"
            )

        cost_basis = (
            qty * avg_price
        )

        current_value = (
            qty * px
        )

        unrealized_pnl = (
            current_value
            - cost_basis
        )

        pnl_pct = (
            unrealized_pnl
            / cost_basis
            if cost_basis > 0
            else 0.0
        )

        weight = allocation.get(
            symbol
        )

        positions.append({
            "symbol": symbol,
            "weight": (
                round(
                    float(weight),
                    6,
                )
                if weight is not None
                else None
            ),
            "price": round(
                px,
                8,
            ),
            "price_eur": round(
                px,
                8,
            ),
            "avg_price": round(
                avg_price,
                8,
            ),
            "avg_price_eur": round(
                avg_price,
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
                pricing.fx.get(
                    "pair"
                ),
            "fx_provider":
                pricing.fx.get(
                    "provider"
                ),
            "fx_market_timestamp":
                pricing.fx.get(
                    "market_timestamp"
                ),
            "qty": round(
                qty,
                8,
            ),
            "cost_basis_eur":
                round(
                    cost_basis,
                    2,
                ),
            "value_eur": round(
                current_value,
                2,
            ),
            "unrealized_pnl_eur":
                round(
                    unrealized_pnl,
                    2,
                ),
            "pnl_pct": round(
                pnl_pct,
                6,
            ),
        })

        total_value += (
            current_value
        )
        total_cost_basis += (
            cost_basis
        )
        total_unrealized += (
            unrealized_pnl
        )

    snapshot_positions = int(
        exposure_snapshot.get(
            "open_positions",
            -1,
        )
    )

    snapshot_notional = float(
        exposure_snapshot.get(
            "total_notional_eur",
            -1.0,
        )
    )

    if (
        snapshot_positions
        != len(positions)
    ):
        raise RuntimeError(
            "metals exposure snapshot "
            "position count mismatch: "
            f"snapshot={snapshot_positions} "
            f"state={len(positions)}"
        )

    # Snapshot sums values already rounded
    # per position. State sums full precision
    # then rounds globally.
    snapshot_cents = round(
        snapshot_notional * 100
    )
    state_cents = round(
        total_value * 100
    )

    reconciliation_tolerance_cents = max(
        1,
        len(positions),
    )

    if (
        abs(
            snapshot_cents
            - state_cents
        )
        > reconciliation_tolerance_cents
    ):
        raise RuntimeError(
            "metals exposure snapshot "
            "notional mismatch: "
            f"snapshot={snapshot_notional} "
            f"state={round(total_value, 2)} "
            "delta_cents="
            f"{abs(snapshot_cents - state_cents)} "
            "tolerance_cents="
            f"{reconciliation_tolerance_cents}"
        )

    payload = {
        "status": "ok",
        "engine":
            "metals_state_updater_v2",
        "generated_at":
            now_iso(),
        "brick": "precious_metals",
        "state_origin":
            "simulated_broker",
        "execution_mode":
            exposure_snapshot.get(
                "execution_mode"
            ),
        "regime":
            signal.get(
                "regime",
                "unknown",
            ),
        "confidence":
            signal.get(
                "confidence",
                0.0,
            ),
        "target_exposure":
            signal.get(
                "target_exposure",
                0.0,
            ),
        "target_amount_eur":
            round(
                target_amount,
                2,
            ),
        "current_exposure_eur":
            round(
                total_value,
                2,
            ),
        "cost_basis_eur":
            round(
                total_cost_basis,
                2,
            ),
        "realized_pnl_eur":
            round(
                realized_pnl,
                2,
            ),
        "unrealized_pnl_eur":
            round(
                total_unrealized,
                2,
            ),
        "pnl_eur":
            round(
                realized_pnl
                + total_unrealized,
                2,
            ),
        "mark_to_market": True,
        "positions":
            positions,
        "positions_count":
            len(positions),
        "fills_count":
            len(fills),
        "broker_positions_source":
            str(POSITIONS_PATH),
        "fills_source":
            str(FILLS_PATH),
        "exposure_source":
            str(EXPOSURE_PATH),
    }

    save_json(
        OUT_PATH,
        payload,
    )

    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )

    return payload


if __name__ == "__main__":
    main()
