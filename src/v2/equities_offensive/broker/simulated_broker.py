#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.equities_offensive.core.state_store import StateStore

def data_root() -> Path:
    import os
    return Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

ROOT = data_root()

PLAN_PATH = ROOT / "equities_offensive/execution/execution_plan.json"
FILLS_PATH = ROOT / "equities_offensive/execution/simulated_fills.jsonl"
POSITIONS_PATH = ROOT / "equities_offensive/state/positions.json"
EXPOSURE_PATH = ROOT / "equities_offensive/state/exposure_snapshot.json"

PRICES_PATH = ROOT / "equities_offensive/market/prices.json"  # optional

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
    Reads offensive equity prices from either:
      - {"prices": {"META": 470.8}}
      - {"META": 470.8}
    Falls back only if no valid positive price is found.
    """
    sym = str(symbol or "").strip().upper()
    doc = load_json(PRICES_PATH, default=None)

    if isinstance(doc, dict):
        prices = doc.get("prices") if isinstance(doc.get("prices"), dict) else doc
        if isinstance(prices, dict):
            for key in (sym, sym.lower(), symbol):
                try:
                    px = prices.get(key)
                    if px is not None and float(px) > 0:
                        return float(px)
                except Exception:
                    continue

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
    Validate / filter orders in an execution plan using shared order_validation utilities.

    Returns:
        (orders, rejected_events)
    """
    from pathlib import Path

    orders = plan.get("orders") or []
    if not isinstance(orders, list):
        orders = []

    rejected_events = []

    # Ensure reject journal exists (brick-only)
    rejected_path = Path("/opt/nsc/data/preprod/equities_offensive/execution/rejected_orders.jsonl")
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.touch(exist_ok=True)

    try:
        # Shared validator (should exist)
        from src.v2.execution.order_validation import validate_execution_plan  # type: ignore

        res = validate_execution_plan(plan)

        # Accept multiple possible return shapes (tuple, dict, list)
        if isinstance(res, tuple) and len(res) == 2:
            v_orders, v_rejected = res
            if isinstance(v_orders, list):
                orders = v_orders
            if isinstance(v_rejected, list):
                rejected_events = v_rejected

        elif isinstance(res, dict):
            v_orders = res.get("orders") or res.get("valid_orders") or res.get("validated_orders")
            v_rejected = res.get("rejected") or res.get("rejected_events") or res.get("rejects")
            if isinstance(v_orders, list):
                orders = v_orders
            if isinstance(v_rejected, list):
                rejected_events = v_rejected

        elif isinstance(res, list):
            # assume it's the filtered orders
            orders = res

    except Exception as e:
        # Fail-safe: do not break broker, keep original orders
        rejected_events.append({
            "ts": utc_now_iso(),
            "engine": "order_validation_wrapper",
            "scope": scope,
            "plan_id": plan_id,
            "status": "ERROR",
            "reason": f"validate_execution_plan failed: {type(e).__name__}: {e}",
        })

    # Normalize + enrich rejected events and persist
    norm_rejected = []
    for ev in (rejected_events or []):
        if not isinstance(ev, dict):
            continue
        ev = dict(ev)
        ev.setdefault("ts", utc_now_iso())
        ev.setdefault("engine", "order_validation")
        ev.setdefault("scope", scope)
        ev.setdefault("plan_id", plan_id)
        norm_rejected.append(ev)

    # Write to jsonl (append_jsonl already exists in this file)
    for ev in norm_rejected:
        try:
            append_jsonl(rejected_path, ev)
        except Exception:
            pass

    # Ensure orders are dicts only
    orders = [o for o in orders if isinstance(o, dict)]
    return orders, norm_rejected




def _parse_iso_ts(value):
    # stdlib only, tolerant
    try:
        from datetime import datetime
        v = str(value).strip()
        if not v:
            return None
        # accept "Z"
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        return datetime.fromisoformat(v)
    except Exception:
        return None

def _is_plan_stale(plan: dict) -> bool:
    """
    Returns True if plan is older than NSC_EQU_PLAN_MAX_AGE_MIN minutes.
    If ts is missing/unparseable => not stale (fail-open).
    """
    try:
        import os
        from datetime import datetime, timezone, timedelta

        max_age = os.getenv("NSC_EQU_PLAN_MAX_AGE_MIN", "").strip()
        max_age_min = int(max_age) if max_age else 180  # default 3h
        if max_age_min <= 0:
            return False

        ts = plan.get("ts") or plan.get("generated_at") or plan.get("created_at")
        dt = _parse_iso_ts(ts) if ts else None
        if dt is None:
            return False

        # normalize timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - dt
        return age > timedelta(minutes=max_age_min)
    except Exception:
        return False

def _ensure_plan_rollover(state: dict, plan_id: str) -> None:
    """
    If plan_id changes, reset orders_seen so idempotence doesn't block a new plan.
    """
    try:
        prev = state.get("orders_seen_plan_id")
        if prev != plan_id:
            state["orders_seen_plan_id"] = plan_id
            state["orders_seen"] = []
    except Exception:
        # fail-open
        pass

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

        # Plan rollover: reset idempotence when plan_id changes
        _ensure_plan_rollover(state, plan_id)

        # Stale plan guard: skip if plan too old
        if _is_plan_stale(plan):
            payload = {"ts": utc_now_iso(), "plan_id": plan_id, "fills_created": 0, "status": "SKIPPED_STALE_PLAN"}
            _set_last_broker_run(store, state, payload)
            store.save(state)
            print({"plan_id": plan_id, "policy": policy, "fills_created": 0, "status": "SKIPPED_STALE_PLAN"})
            return


        # Idempotence at order level
        seen = _get_orders_seen(store, state)

        # In preprod we expect SIMULATED_ONLY (orders likely empty),
        # but we still support sim fills if orders exist.
        created = 0

        # Ensure fills file exists even when no fills are created
        FILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        FILLS_PATH.touch(exist_ok=True)

        REJECTED_PATH = Path("/opt/nsc/data/preprod/equities_offensive/execution/rejected_orders.jsonl")
        REJECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
        REJECTED_PATH.touch(exist_ok=True)

        positions = load_positions()

        for o in orders:
            if not isinstance(o, dict):
                try:
                    append_jsonl(REJECTED_PATH, {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": "order_not_a_dict",
                        "order_raw": str(o),
                    })
                except Exception:
                    pass
                continue

            symbol = o.get("symbol")
            side = (o.get("side") or "").upper()
            qty = o.get("qty")

            if not symbol:
                try:
                    append_jsonl(REJECTED_PATH, {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": "missing_symbol",
                        "order": o,
                    })
                except Exception:
                    pass
                continue

            if side not in {"BUY", "SELL"}:
                try:
                    append_jsonl(REJECTED_PATH, {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": "invalid_side",
                        "order": o,
                    })
                except Exception:
                    pass
                continue

            try:
                qty = float(qty)
            except Exception:
                try:
                    append_jsonl(REJECTED_PATH, {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": "invalid_qty_type",
                        "order": o,
                    })
                except Exception:
                    pass
                continue

            if qty <= 0:
                try:
                    append_jsonl(REJECTED_PATH, {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": "qty_le_zero",
                        "order": o,
                    })
                except Exception:
                    pass
                continue

            requested_qty = qty

            oid = plan_order_id(
                plan_id,
                {
                    "symbol": symbol,
                    "side": side,
                    "qty": requested_qty,
                    "type": o.get("type"),
                    "limit_price": o.get("limit_price"),
                },
            )

            if oid in seen:
                continue

            effective_qty = requested_qty
            quantity_adjustment = None

            if side == "SELL":
                current_position = positions.get(symbol)
                current_qty = float(
                    getattr(current_position, "qty", 0.0) or 0.0
                )

                if current_qty <= 0:
                    append_jsonl(
                        REJECTED_PATH,
                        {
                            "ts": utc_now_iso(),
                            "engine": "simulated_broker_v1",
                            "plan_id": plan_id,
                            "order_id": oid,
                            "policy": policy,
                            "status": "REJECTED",
                            "reason": "sell_without_open_position",
                            "symbol": symbol,
                            "side": side,
                            "requested_qty": requested_qty,
                            "available_qty": current_qty,
                            "order": o,
                        },
                    )

                    _mark_order_seen(store, state, oid)
                    continue

                if requested_qty > current_qty:
                    effective_qty = current_qty
                    quantity_adjustment = {
                        "reason": "sell_qty_capped_to_available_position",
                        "requested_qty": requested_qty,
                        "available_qty": current_qty,
                        "executed_qty": effective_qty,
                    }

            if effective_qty <= 0:
                append_jsonl(
                    REJECTED_PATH,
                    {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "order_id": oid,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": "effective_qty_le_zero",
                        "symbol": symbol,
                        "side": side,
                        "requested_qty": requested_qty,
                        "effective_qty": effective_qty,
                        "order": o,
                    },
                )

                _mark_order_seen(store, state, oid)
                continue

            # In SIMULATED_ONLY mode, fills remain strictly simulated.
            # The fill ledger records the quantity actually applied to the position.
            price = get_price(symbol, fallback=100.0)

            fill = {
                "ts": utc_now_iso(),
                "engine": "simulated_broker_v1",
                "plan_id": plan_id,
                "order_id": oid,
                # Current simulator creates exactly one fill per order.
                # A future broker adapter supporting partial fills must
                # provide a broker-native unique fill identifier.
                "fill_id": f"simfill:{oid}",
                "policy": policy,
                "symbol": symbol,
                "side": side,
                "qty": effective_qty,
                "requested_qty": requested_qty,
                "fill_price": price,
                "commission_usd": 0.0,
                "fees_usd": 0.0,
                "status": "FILLED",
            }

            if quantity_adjustment is not None:
                fill["quantity_adjustment"] = quantity_adjustment

            append_jsonl(FILLS_PATH, fill)

            apply_fill(
                positions,
                symbol,
                side,
                effective_qty,
                price,
            )

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
