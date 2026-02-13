#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.equities_offensive.core.state_store import StateStore

PLAN_PATH = Path("data/equities_offensive/execution/execution_plan.json")
FILLS_PATH = Path("data/equities_offensive/execution/simulated_fills.jsonl")
POSITIONS_PATH = Path("data/equities_offensive/state/positions.json")
EXPOSURE_PATH = Path("data/equities_offensive/state/exposure_snapshot.json")

PRICES_PATH = Path("data/equities_offensive/market/prices.json")  # optional

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def sha16(obj: Any) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def get_price(symbol: str, fallback: float = 100.0) -> float:
    """
    Price feed optional. If missing, fallback constant price (paper trading only).
    You can later wire a real price snapshot.
    """
    doc = load_json(PRICES_PATH, default=None)
    if isinstance(doc, dict):
        px = doc.get(symbol)
        try:
            if px is not None:
                return float(px)
        except Exception:
            pass
    return float(fallback)

@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0

def load_positions() -> Dict[str, Position]:
    doc = load_json(POSITIONS_PATH, default={}) or {}
    out: Dict[str, Position] = {}
    if isinstance(doc, dict):
        for sym, d in doc.items():
            if not isinstance(d, dict):
                continue
            try:
                out[sym] = Position(sym, float(d.get("qty", 0.0)), float(d.get("avg_price", 0.0)))
            except Exception:
                continue
    return out

def save_positions(pos: Dict[str, Position]) -> None:
    doc = {sym: {"qty": p.qty, "avg_price": p.avg_price} for sym, p in pos.items()}
    save_json(POSITIONS_PATH, doc)

def apply_fill(pos: Dict[str, Position], symbol: str, side: str, qty: float, price: float) -> None:
    p = pos.get(symbol, Position(symbol))
    if side == "BUY":
        new_qty = p.qty + qty
        if new_qty <= 0:
            p.qty = 0.0
            p.avg_price = 0.0
        else:
            # weighted avg
            p.avg_price = (p.avg_price * p.qty + price * qty) / new_qty if p.qty > 0 else price
            p.qty = new_qty
    elif side == "SELL":
        new_qty = p.qty - qty
        if new_qty <= 0:
            p.qty = 0.0
            p.avg_price = 0.0
        else:
            p.qty = new_qty
            # avg_price unchanged on partial sell
    pos[symbol] = p

def build_exposure_snapshot(pos: Dict[str, Position]) -> Dict[str, Any]:
    total_notional = 0.0
    lines = []
    for sym, p in pos.items():
        if p.qty <= 0:
            continue
        px = get_price(sym, fallback=p.avg_price or 100.0)
        notion = px * p.qty
        total_notional += notion
        lines.append({"symbol": sym, "qty": p.qty, "price": px, "notional_usd": notion})
    return {
        "ts": utc_now_iso(),
        "engine": "simulated_broker_v1",
        "open_positions": len(lines),
        "total_notional_usd": round(total_notional, 2),
        "positions": lines,
    }



def _get_orders_seen(store, state) -> set:
    """
    Backward-compatible: uses StateStore methods if available,
    otherwise uses state['orders_seen'] list.
    """
    if hasattr(store, "get_orders_seen"):
        try:
            seen = _get_orders_seen(store, state)
            return set(seen) if isinstance(seen, (list, set, tuple)) else set()
        except Exception:
            pass
    seen = state.get("orders_seen")
    if not isinstance(seen, list):
        seen = []
        state["orders_seen"] = seen
    return set(seen)

def _mark_order_seen(store, state, order_id: str) -> None:
    if hasattr(store, "mark_order_seen"):
        try:
            store.mark_order_seen(state, order_id)
            return
        except Exception:
            pass
    seen = state.get("orders_seen")
    if not isinstance(seen, list):
        seen = []
        state["orders_seen"] = seen
    if order_id not in seen:
        seen.append(order_id)

def _set_last_broker_run(store, state, payload: dict) -> None:
    if hasattr(store, "set_last_broker_run"):
        try:
            store.set_last_broker_run(state, payload)
            return
        except Exception:
            pass
    state["last_broker_run"] = payload

def plan_order_id(plan_id: str, order: Dict[str, Any]) -> str:
    # deterministic per plan + order payload
    payload = {"plan_id": plan_id, "order": order}
    return f"ord_{sha16(payload)}"


def _normalize_order_for_oid(o: dict) -> dict:
    """
    Normalize order fields so our deterministic oid remains stable across
    plan versions (order_type vs type, limit_price vs price, etc.).
    """
    if not isinstance(o, dict):
        return {}
    return {
        "symbol": o.get("symbol"),
        "side": (o.get("side") or "").upper(),
        "qty": o.get("qty"),
        "order_type": o.get("order_type") or o.get("type") or o.get("orderType"),
        "limit_price": o.get("limit_price") or o.get("price") or o.get("limitPrice"),
        "time_in_force": o.get("time_in_force") or o.get("tif") or o.get("timeInForce"),
    }


def _validate_orders_with_plan(plan: dict, plan_id: str, scope: str):
    """
    Validate orders using src/v2/execution/order_validation.py when available.
    Fail-safe: if validation is unavailable or errors, return original orders.

    Returns: (valid_orders, rejected_events)
    rejected_events are jsonl entries written to FILLS_PATH with status=REJECTED.
    """
    orders = plan.get("orders") or []
    # Validate orders (EXE-002)
    orders, rejected_events = _validate_orders_with_plan(
        plan, plan_id, scope="equities_offensive"
    )
    for ev in rejected_events:
        append_jsonl(FILLS_PATH, ev)
    if not isinstance(orders, list):
        return [], []

    # Lazy import + signature-tolerant call
    validator = None
    try:
        from src.v2.execution.order_validation import validate_execution_plan  # type: ignore
        validator = validate_execution_plan
    except Exception:
        try:
            from v2.execution.order_validation import validate_execution_plan  # type: ignore
            validator = validate_execution_plan
        except Exception:
            validator = None

    if validator is None:
        return orders, []

    result = None
    try:
        result = validator(plan, scope=scope)
    except TypeError:
        try:
            result = validator(plan, scope)
        except TypeError:
            try:
                result = validator(plan)
            except Exception:
                return orders, []
    except Exception:
        return orders, []

    valid_orders = orders
    rejected = []

    if isinstance(result, list):
        valid_orders = result
        rejected = []
    elif isinstance(result, dict):
        valid_orders = result.get("orders") or result.get("validated_orders") or orders
        rejected = result.get("rejected") or result.get("rejected_orders") or []

    rejected_events = []
    if isinstance(rejected, list):
        for r in rejected:
            if isinstance(r, dict):
                o = r.get("order") if isinstance(r.get("order"), dict) else r
                reasons = r.get("reasons") or r.get("errors") or r.get("reason") or r.get("message")
            else:
                o = {}
                reasons = str(r)

            payload = _normalize_order_for_oid(o)
            try:
                qty = float(payload.get("qty") or 0)
            except Exception:
                qty = 0.0

            symbol = payload.get("symbol")
            side = payload.get("side")

            oid = plan_order_id(plan_id, {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "type": payload.get("order_type"),
                "limit_price": payload.get("limit_price"),
            }) if (symbol and side) else f"rej_{sha16({'plan_id': plan_id, 'raw': o})}"

            rejected_events.append({
                "ts": utc_now_iso(),
                "engine": "order_validation_v1",
                "plan_id": plan_id,
                "order_id": oid,
                "policy": (plan.get("action_policy") or "SIMULATED_ONLY").upper(),
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "status": "REJECTED",
                "reasons": reasons if isinstance(reasons, list) else [str(reasons)] if reasons else ["validation_failed"],
                "raw_order": o,
            })

    return valid_orders if isinstance(valid_orders, list) else orders, rejected_events

def main():
    store = StateStore()
    store.with_lock()
    try:
        state = store.load()

        plan = load_json(PLAN_PATH, default=None)
        if not isinstance(plan, dict):
            print("No execution_plan.json")
            return

        plan_id = plan.get("plan_id")
        policy = (plan.get("action_policy") or "SIMULATED_ONLY").upper()
        orders = plan.get("orders") or []

        if not plan_id:
            print("Plan missing plan_id")
            return

        # Idempotence at order level
        seen = _get_orders_seen(store, state)

        # In preprod we expect SIMULATED_ONLY (orders likely empty),
        # but we still support sim fills if orders exist.
        created = 0

        # Ensure fills file exists even when no fills are created
        FILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        FILLS_PATH.touch(exist_ok=True)
        positions = load_positions()

        for o in orders:
            if not isinstance(o, dict):
                continue
            symbol = o.get("symbol")
            side = (o.get("side") or "").upper()
            qty = o.get("qty")
            if not symbol or side not in {"BUY", "SELL"}:
                continue
            try:
                qty = float(qty)
            except Exception:
                continue
            if qty <= 0:
                continue

            oid = plan_order_id(plan_id, {"symbol": symbol, "side": side, "qty": qty, "type": o.get("type"), "limit_price": o.get("limit_price")})
            if oid in seen:
                continue

            # If policy is SIMULATED_ONLY, we still record simulated fills (paper trading),
            # but never mark as "live".
            price = get_price(symbol, fallback=100.0)

            fill = {
                "ts": utc_now_iso(),
                "engine": "simulated_broker_v1",
                "plan_id": plan_id,
                "order_id": oid,
                "policy": policy,
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "fill_price": price,
                "status": "FILLED",
            }
            append_jsonl(FILLS_PATH, fill)
            apply_fill(positions, symbol, side, qty, price)

            _mark_order_seen(store, state, oid)
            created += 1

        save_positions(positions)
        snap = build_exposure_snapshot(positions)
        save_json(EXPOSURE_PATH, snap)

        _set_last_broker_run(store, state, {"ts": utc_now_iso(), "plan_id": plan_id, "fills_created": created})
        store.save(state)

        print(json.dumps({"plan_id": plan_id, "policy": policy, "fills_created": created}, ensure_ascii=False, indent=2))

    finally:
        store.close()

if __name__ == "__main__":
    main()
