from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


EPSILON = 1e-9


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _canonical_hash(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:24]


def get_fill_identity(
    fill: Dict[str, Any],
    sequence: Optional[int] = None,
) -> str:
    """
    Return a stable identity for deduplication.

    Priority:
    1. explicit fill_id;
    2. order_id for current simulated broker, which creates one fill
       per order;
    3. deterministic content hash for legacy fills.
    """
    fill_id = str(fill.get("fill_id") or "").strip()
    if fill_id:
        return fill_id

    order_id = str(fill.get("order_id") or "").strip()
    if order_id:
        return f"legacy-order-fill:{order_id}"

    identity_payload = {
        "ts": fill.get("ts"),
        "plan_id": fill.get("plan_id"),
        "symbol": fill.get("symbol"),
        "side": fill.get("side"),
        "qty": fill.get("qty"),
        "fill_price": (
            fill.get("fill_price")
            if fill.get("fill_price") is not None
            else fill.get("price")
        ),
        "status": fill.get("status"),
        "sequence": sequence,
    }

    return f"legacy-hash-fill:{_canonical_hash(identity_payload)}"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue

        try:
            row = json.loads(line)
        except Exception:
            rows.append(
                {
                    "_raw_line_error": True,
                    "_line_number": line_number,
                    "_raw": line,
                }
            )
            continue

        if isinstance(row, dict):
            row.setdefault("_line_number", line_number)
            rows.append(row)

    return rows


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from src.v2.utils.file_utils import save_json_file

        save_json_file(str(path), payload)
    except Exception:
        path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def build_trade_ledger(
    fills: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Rebuild a long-only trade ledger from immutable fills.

    Accounting method:
    - BUY: weighted-average cost, with buy fees capitalized.
    - partial SELL: average price remains unchanged.
    - SELL realized P&L:
        net proceeds - released average cost.
    - full SELL: remaining quantity and average price become zero.
    """
    positions: Dict[str, Dict[str, float]] = {}
    events: List[Dict[str, Any]] = []
    anomalies: List[str] = []
    seen_fill_ids = set()

    fills_total = 0
    fills_processed = 0
    duplicate_fills = 0
    realized_pnl_usd = 0.0
    gross_proceeds_usd = 0.0
    total_fees_usd = 0.0
    buy_notional_usd = 0.0
    sell_notional_usd = 0.0

    for sequence, fill in enumerate(fills, start=1):
        fills_total += 1

        if not isinstance(fill, dict):
            anomalies.append(
                f"invalid_fill_object:sequence={sequence}"
            )
            continue

        if fill.get("_raw_line_error"):
            anomalies.append(
                "invalid_jsonl_line:"
                f"{fill.get('_line_number', sequence)}"
            )
            continue

        status = str(
            fill.get("status") or ""
        ).strip().upper()

        if status != "FILLED":
            continue

        symbol = str(
            fill.get("symbol") or ""
        ).strip().upper()

        side = str(
            fill.get("side") or ""
        ).strip().upper()

        qty = _number(fill.get("qty"))
        price = _number(
            fill.get("fill_price")
            if fill.get("fill_price") is not None
            else fill.get("price")
        )

        commission = _number(
            fill.get("commission_usd")
        )
        fees = _number(fill.get("fees_usd"))
        total_fill_fees = commission + fees

        fill_id = get_fill_identity(
            fill,
            sequence=sequence,
        )

        if fill_id in seen_fill_ids:
            duplicate_fills += 1
            continue

        seen_fill_ids.add(fill_id)

        if not symbol:
            anomalies.append(
                f"missing_symbol:fill_id={fill_id}"
            )
            continue

        if side not in {"BUY", "SELL"}:
            anomalies.append(
                f"invalid_side:{symbol}:fill_id={fill_id}"
            )
            continue

        if qty <= 0:
            anomalies.append(
                f"non_positive_qty:{symbol}:fill_id={fill_id}"
            )
            continue

        if price <= 0:
            anomalies.append(
                f"non_positive_price:{symbol}:fill_id={fill_id}"
            )
            continue

        if total_fill_fees < 0:
            anomalies.append(
                f"negative_fees:{symbol}:fill_id={fill_id}"
            )
            continue

        position = positions.setdefault(
            symbol,
            {
                "qty": 0.0,
                "avg_price": 0.0,
                "realized_pnl_usd": 0.0,
            },
        )

        qty_before = float(position["qty"])
        avg_before = float(position["avg_price"])
        gross_notional = qty * price
        event_realized_pnl = 0.0
        cost_basis_released = 0.0
        net_proceeds = 0.0

        if side == "BUY":
            new_qty = qty_before + qty
            existing_cost = qty_before * avg_before
            acquired_cost = gross_notional + total_fill_fees

            new_avg = (
                (existing_cost + acquired_cost) / new_qty
                if new_qty > EPSILON
                else 0.0
            )

            position["qty"] = new_qty
            position["avg_price"] = new_avg

            buy_notional_usd += gross_notional

        else:
            if qty_before <= EPSILON:
                anomalies.append(
                    "sell_without_open_position:"
                    f"{symbol}:fill_id={fill_id}"
                )
                continue

            if qty > qty_before + EPSILON:
                anomalies.append(
                    "sell_qty_exceeds_position:"
                    f"{symbol}:fill_id={fill_id}:"
                    f"sell_qty={qty}:available_qty={qty_before}"
                )
                continue

            cost_basis_released = qty * avg_before
            net_proceeds = gross_notional - total_fill_fees
            event_realized_pnl = (
                net_proceeds - cost_basis_released
            )

            new_qty = qty_before - qty

            if new_qty <= EPSILON:
                new_qty = 0.0
                new_avg = 0.0
            else:
                new_avg = avg_before

            position["qty"] = new_qty
            position["avg_price"] = new_avg
            position["realized_pnl_usd"] += (
                event_realized_pnl
            )

            realized_pnl_usd += event_realized_pnl
            gross_proceeds_usd += gross_notional
            sell_notional_usd += gross_notional

        total_fees_usd += total_fill_fees
        fills_processed += 1

        events.append(
            {
                "sequence": sequence,
                "fill_id": fill_id,
                "order_id": fill.get("order_id"),
                "plan_id": fill.get("plan_id"),
                "ts": fill.get("ts"),
                "symbol": symbol,
                "side": side,
                "qty": round(qty, 12),
                "fill_price": round(price, 12),
                "gross_notional_usd": round(
                    gross_notional,
                    8,
                ),
                "commission_usd": round(
                    commission,
                    8,
                ),
                "fees_usd": round(fees, 8),
                "total_fill_fees_usd": round(
                    total_fill_fees,
                    8,
                ),
                "qty_before": round(qty_before, 12),
                "avg_price_before": round(
                    avg_before,
                    12,
                ),
                "cost_basis_released_usd": round(
                    cost_basis_released,
                    8,
                ),
                "net_proceeds_usd": round(
                    net_proceeds,
                    8,
                ),
                "realized_pnl_usd": round(
                    event_realized_pnl,
                    8,
                ),
                "qty_after": round(
                    position["qty"],
                    12,
                ),
                "avg_price_after": round(
                    position["avg_price"],
                    12,
                ),
                "status": "REALIZED"
                if side == "SELL"
                else "OPENING_OR_INCREASE",
            }
        )

    open_positions: Dict[str, Dict[str, float]] = {}
    per_symbol: Dict[str, Dict[str, float]] = {}

    for symbol, position in sorted(positions.items()):
        qty = float(position["qty"])
        avg_price = float(position["avg_price"])
        symbol_realized = float(
            position["realized_pnl_usd"]
        )

        per_symbol[symbol] = {
            "qty": round(qty, 12),
            "avg_price": round(avg_price, 12),
            "cost_basis_usd": round(
                qty * avg_price,
                8,
            ),
            "realized_pnl_usd": round(
                symbol_realized,
                8,
            ),
        }

        if qty > EPSILON:
            open_positions[symbol] = dict(
                per_symbol[symbol]
            )

    return {
        "ts": utc_now_iso(),
        "engine": "equities_offensive_trade_ledger_v1",
        "accounting_method": (
            "weighted_average_cost_long_only"
        ),
        "currency": "USD",
        "summary": {
            "fills_total": fills_total,
            "fills_processed": fills_processed,
            "duplicate_fills_ignored": duplicate_fills,
            "buy_notional_usd": round(
                buy_notional_usd,
                8,
            ),
            "sell_notional_usd": round(
                sell_notional_usd,
                8,
            ),
            "gross_proceeds_usd": round(
                gross_proceeds_usd,
                8,
            ),
            "total_fees_usd": round(
                total_fees_usd,
                8,
            ),
            "realized_pnl_usd": round(
                realized_pnl_usd,
                8,
            ),
            "closed_trade_events": sum(
                1
                for event in events
                if event["side"] == "SELL"
            ),
            "open_positions": len(open_positions),
            "anomalies_count": len(anomalies),
        },
        "per_symbol": per_symbol,
        "open_positions": open_positions,
        "events": events,
        "anomalies": anomalies,
        "ok": len(anomalies) == 0,
    }


def build_trade_ledger_from_path(
    fills_path: Path,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    ledger = build_trade_ledger(
        read_jsonl(fills_path)
    )

    ledger["fills_path"] = str(fills_path)

    if output_path is not None:
        ledger["output_path"] = str(output_path)
        save_json(output_path, ledger)

    return ledger
