from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.v2.market.preprod_price_contract import load_fresh_prices
from src.v2.defensive_equities.common import load_defensive_universe
from src.v2.defensive_equities.eur_pricing import build_eur_prices


ROOT = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

SIGNAL_PATH = ROOT / "defensive/defensive_signal.json"
PORTFOLIO_STATE_PATH = ROOT / "portfolio/state/portfolio_state.json"
PRICES_PATH = ROOT / "defensive/prices.json"

POSITIONS_PATH = ROOT / "defensive/state/positions.json"
FILLS_PATH = ROOT / "defensive/execution/simulated_fills.jsonl"
EXPOSURE_PATH = ROOT / "defensive/state/exposure_snapshot.json"

OUT_PATH = ROOT / "defensive/defensive_state.json"

MAX_PRICE_AGE_SECONDS = 6 * 60 * 60


def load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []

    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            row = json.loads(line)
        except Exception as exc:
            raise RuntimeError(
                f"invalid defensive fill JSON at line {line_no}: {exc}"
            ) from exc

        if not isinstance(row, dict):
            raise RuntimeError(
                f"invalid defensive fill at line {line_no}: expected object"
            )

        rows.append(row)

    return rows


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def realized_pnl_from_fills(fills: List[Dict[str, Any]]) -> float:
    total = 0.0

    for row in fills:
        if str(row.get("status") or "").upper() != "FILLED":
            continue

        if str(row.get("side") or "").upper() != "SELL":
            continue

        try:
            total += float(
                row.get("realized_pnl_eur", 0.0) or 0.0
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "invalid realized_pnl_eur in defensive fills"
            ) from exc

    return round(total, 8)


def build_asset_metadata(signal: dict) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}

    proposed_assets = signal.get("proposed_assets") or []

    if not isinstance(proposed_assets, list):
        return out

    for row in proposed_assets:
        if not isinstance(row, dict):
            continue

        symbol = str(row.get("ticker") or "").strip().upper()
        if not symbol:
            continue

        out[symbol] = {
            "weight": row.get("weight"),
            "type": row.get("type"),
            "sector": row.get("sector"),
            "region": row.get("region"),
        }

    return out


def main():
    signal = load_json(SIGNAL_PATH, default=None)
    portfolio_state = load_json(PORTFOLIO_STATE_PATH, default=None)
    broker_positions = load_json(POSITIONS_PATH, default=None)
    exposure_snapshot = load_json(EXPOSURE_PATH, default=None)

    if not isinstance(signal, dict):
        raise RuntimeError("defensive signal missing or invalid")

    if not isinstance(portfolio_state, dict):
        raise RuntimeError("portfolio state missing or invalid")

    if not isinstance(broker_positions, dict):
        raise RuntimeError(
            "defensive broker positions missing or invalid; "
            "state updater refuses synthetic reconstruction"
        )

    if not isinstance(exposure_snapshot, dict):
        raise RuntimeError(
            "defensive broker exposure snapshot missing or invalid"
        )

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

    fills = load_jsonl(FILLS_PATH)
    realized_pnl = realized_pnl_from_fills(fills)

    defensive = (
        (portfolio_state.get("bricks") or {})
        .get("equities_defensive", {})
        or {}
    )

    target_exposure = float(
        signal.get("target_exposure", 0.0) or 0.0
    )
    target_amount = float(
        defensive.get("target_amount_eur", 0.0) or 0.0
    )

    metadata = build_asset_metadata(signal)

    positions = []
    total_value = 0.0
    total_cost_basis = 0.0
    total_unrealized = 0.0

    for symbol, row in sorted(broker_positions.items()):
        if not isinstance(row, dict):
            raise RuntimeError(
                f"invalid defensive broker position for {symbol}"
            )

        qty = float(row.get("qty", 0.0) or 0.0)
        avg_price = float(row.get("avg_price", 0.0) or 0.0)

        if qty <= 0:
            continue

        if avg_price <= 0:
            raise RuntimeError(
                f"invalid defensive avg_price for {symbol}"
            )

        px = float(prices.get(symbol, 0.0) or 0.0)

        if px <= 0:
            raise RuntimeError(
                f"missing valid defensive mark price for {symbol}"
            )

        cost_basis = qty * avg_price
        current_value = qty * px
        unrealized_pnl = current_value - cost_basis
        pnl_pct = (
            unrealized_pnl / cost_basis
            if cost_basis > 0
            else 0.0
        )

        meta = metadata.get(symbol, {})
        pricing = eur_pricing.get(symbol)

        if pricing is None:
            raise RuntimeError(
                f"missing defensive EUR pricing for {symbol}"
            )

        positions.append({
            "symbol": symbol,
            "weight": (
                round(float(meta.get("weight")), 6)
                if meta.get("weight") is not None
                else None
            ),
            "price": round(px, 8),
            "price_eur": round(px, 8),
            "avg_price": round(avg_price, 8),
            "avg_price_eur": round(avg_price, 8),
            "native_price": round(
                pricing.native_price,
                8,
            ),
            "native_currency": pricing.native_currency,
            "yahoo_symbol": pricing.yahoo_symbol,
            "fx_to_eur": round(
                pricing.fx_to_eur,
                12,
            ),
            "fx_pair": pricing.fx.get("pair"),
            "fx_provider": pricing.fx.get("provider"),
            "fx_market_timestamp": pricing.fx.get(
                "market_timestamp"
            ),
            "qty": round(qty, 8),
            "cost_basis_eur": round(cost_basis, 2),
            "value_eur": round(current_value, 2),
            "unrealized_pnl_eur": round(unrealized_pnl, 2),
            "pnl_pct": round(pnl_pct, 6),
            "type": meta.get("type"),
            "sector": meta.get("sector"),
            "region": meta.get("region"),
        })

        total_value += current_value
        total_cost_basis += cost_basis
        total_unrealized += unrealized_pnl

    snapshot_positions = int(
        exposure_snapshot.get("open_positions", -1)
    )
    snapshot_notional = float(
        exposure_snapshot.get("total_notional_eur", -1.0)
    )

    if snapshot_positions != len(positions):
        raise RuntimeError(
            "defensive exposure snapshot position count mismatch: "
            f"snapshot={snapshot_positions} state={len(positions)}"
        )

    # Snapshot notionals are rounded per position before summation,
    # while state valuation is summed at full precision then rounded.
    # Reconcile in integer cents and allow at most one cent of
    # aggregation drift per open position.
    snapshot_cents = round(snapshot_notional * 100)
    state_cents = round(total_value * 100)
    reconciliation_tolerance_cents = max(
        1,
        len(positions),
    )

    if abs(snapshot_cents - state_cents) > reconciliation_tolerance_cents:
        raise RuntimeError(
            "defensive exposure snapshot notional mismatch: "
            f"snapshot={snapshot_notional} "
            f"state={round(total_value, 2)} "
            f"delta_cents={abs(snapshot_cents - state_cents)} "
            f"tolerance_cents={reconciliation_tolerance_cents}"
        )

    payload = {
        "status": "ok",
        "engine": "defensive_state_updater_v2",
        "generated_at": now_iso(),
        "brick": "defensive_equities",
        "state_origin": "simulated_broker",
        "execution_mode": exposure_snapshot.get("execution_mode"),
        "regime": defensive.get(
            "regime",
            signal.get("mode", "stabilization_active"),
        ),
        "confidence": float(
            defensive.get(
                "confidence",
                signal.get("confidence", 0.0),
            )
            or 0.0
        ),
        "target_exposure": target_exposure,
        "target_amount_eur": round(target_amount, 2),
        "current_exposure_eur": round(total_value, 2),
        "cost_basis_eur": round(total_cost_basis, 2),
        "realized_pnl_eur": round(realized_pnl, 2),
        "unrealized_pnl_eur": round(total_unrealized, 2),
        "pnl_eur": round(
            realized_pnl + total_unrealized,
            2,
        ),
        "mark_to_market": True,
        "positions": positions,
        "constraints_respected": (
            signal.get("score_summary", {}) or {}
        ).get("constraints_respected"),
        "portfolio_beta_estimate": (
            signal.get("score_summary", {}) or {}
        ).get("portfolio_beta_estimate"),
        "positions_count": len(positions),
        "fills_count": len(fills),
        "broker_positions_source": str(POSITIONS_PATH),
        "fills_source": str(FILLS_PATH),
        "exposure_source": str(EXPOSURE_PATH),
    }

    save_json(OUT_PATH, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    main()
