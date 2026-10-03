#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.equities_offensive.core.state_store import StateStore
from src.v2.equities_offensive.execution.capacity_guard import build_capacity_contract, admit_buy

def data_root() -> Path:
    import os
    return Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

ROOT = data_root()

PLAN_PATH = ROOT / "equities_offensive/execution/execution_plan.json"
FILLS_PATH = ROOT / "equities_offensive/execution/simulated_fills.jsonl"
REJECTED_PATH = ROOT / "equities_offensive/execution/rejected_orders.jsonl"
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
    from src.v2.utils.file_utils import save_json_file_atomic
    save_json_file_atomic(str(path), data)

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """Durable append for execution journals."""
    import os

    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n"

    with path.open("a", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())


def load_fill_journal_strict(
    fills_path: Path = FILLS_PATH,
) -> List[Dict[str, Any]]:
    """
    Strict immutable fill-journal reader.

    Any malformed FILLED event, missing execution identity,
    or duplicate fill/order identity fails closed.
    """
    if not fills_path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    fill_ids = set()
    order_ids = set()

    with fills_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                continue

            try:
                row = json.loads(raw)
            except Exception as exc:
                raise RuntimeError(
                    f"Corrupt fill journal line {line_no}"
                ) from exc

            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Invalid fill journal row {line_no}"
                )

            if str(row.get("status") or "").upper() != "FILLED":
                raise RuntimeError(
                    f"Unexpected fill journal status line {line_no}"
                )

            fill_id = str(row.get("fill_id") or "").strip()
            order_id = str(row.get("order_id") or "").strip()
            symbol = str(row.get("symbol") or "").strip()
            side = str(row.get("side") or "").upper().strip()

            try:
                qty = float(row.get("qty") or 0.0)
                price = float(row.get("fill_price") or 0.0)
            except Exception as exc:
                raise RuntimeError(
                    f"Invalid fill numeric fields line {line_no}"
                ) from exc

            if (
                not fill_id
                or not order_id
                or not symbol
                or side not in {"BUY", "SELL"}
                or qty <= 0
                or price <= 0
            ):
                raise RuntimeError(
                    f"Incomplete fill journal row {line_no}"
                )

            if fill_id in fill_ids:
                raise RuntimeError(
                    f"Duplicate fill_id in journal: {fill_id}"
                )

            if order_id in order_ids:
                raise RuntimeError(
                    f"Duplicate order_id in journal: {order_id}"
                )

            fill_ids.add(fill_id)
            order_ids.add(order_id)
            rows.append(row)

    return rows


def replay_positions_from_fills(
    rows: List[Dict[str, Any]],
) -> Dict[str, Position]:
    """Deterministically rebuild positions from validated fills."""
    positions: Dict[str, Position] = {}

    for row in rows:
        apply_fill(
            positions,
            str(row["symbol"]).strip(),
            str(row["side"]).upper().strip(),
            float(row["qty"]),
            float(row["fill_price"]),
        )

    return positions


def durable_filled_order_ids(
    fills_path: Path = FILLS_PATH,
) -> set:
    return {
        str(row["order_id"])
        for row in load_fill_journal_strict(fills_path)
    }

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



def positions_document(
    positions: Dict[str, Position],
) -> Dict[str, Dict[str, float]]:
    """Canonical persisted representation of simulator positions."""
    return {
        sym: {
            "qty": p.qty,
            "avg_price": p.avg_price,
        }
        for sym, p in positions.items()
    }


def reconcile_positions_from_fill_journal(
    fills_path: Path = FILLS_PATH,
    positions_path: Path = POSITIONS_PATH,
) -> Tuple[Dict[str, Position], bool]:
    """
    Rebuild the derived position snapshot from the authoritative
    immutable fill journal.

    Returns (positions, repaired).

    Journal corruption/duplicate identity fails closed.
    A missing or divergent derived snapshot is repaired atomically.
    """
    journal_existed = fills_path.exists()
    rows = load_fill_journal_strict(fills_path)
    journal_has_authority = bool(rows)

    # A missing, empty, or whitespace-only journal must never silently
    # erase an existing open-position snapshot. At least one strictly
    # valid durable fill is required before an existing open position
    # may be reconstructed from journal authority.
    if (not journal_has_authority) and positions_path.exists():
        from src.v2.utils.file_utils import load_json_file_strict

        current_positions = load_json_file_strict(
            str(positions_path)
        )
        if not isinstance(current_positions, dict):
            raise RuntimeError(
                "positions snapshot is not a JSON object"
            )

        try:
            has_open_position = any(
                isinstance(v, dict)
                and abs(float(v.get("qty", 0) or 0)) > 0
                for v in current_positions.values()
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "positions snapshot contains invalid quantity"
            ) from exc

        if has_open_position:
            journal_state = (
                "empty_or_non_authoritative"
                if journal_existed
                else "missing"
            )
            raise RuntimeError(
                f"fill journal {journal_state} while open "
                "positions snapshot exists"
            )
    replayed = replay_positions_from_fills(rows)
    expected = positions_document(replayed)

    current = None

    if positions_path.exists():
        try:
            from src.v2.utils.file_utils import (
                load_json_file_strict,
            )
            current = load_json_file_strict(
                str(positions_path)
            )
        except Exception:
            current = None

    if current == expected:
        return replayed, False

    from src.v2.utils.file_utils import save_json_file_atomic

    save_json_file_atomic(
        str(positions_path),
        expected,
    )

    return replayed, True


def _get_orders_seen(store, state) -> set:
    """
    Backward-compatible: uses StateStore methods if available,
    otherwise uses state['orders_seen'] list.
    """
    if hasattr(store, "get_orders_seen"):
        try:
            seen = store.get_orders_seen(state)
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
    orders = plan.get("orders") or []
    if not isinstance(orders, list):
        orders = []

    rejected_events = []

    # Ensure reject journal exists (brick-only)
    REJECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    REJECTED_PATH.touch(exist_ok=True)

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




def filled_buy_economic_signal_ids(
    fills_path=FILLS_PATH,
) -> set:
    """
    Durable economic-consumption authority.

    Only successful BUY fills consume an economic signal.
    Legacy fills without economic_signal_id are intentionally
    grandfathered and do not create inferred identities.
    """
    consumed = set()

    if not fills_path.exists():
        return consumed

    try:
        lines = fills_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return consumed

    for raw in lines:
        raw = raw.strip()

        if not raw:
            continue

        try:
            row = json.loads(raw)
        except Exception:
            continue

        if not isinstance(row, dict):
            continue

        if (
            str(row.get("status") or "").upper()
            != "FILLED"
        ):
            continue

        if (
            str(row.get("side") or "").upper()
            != "BUY"
        ):
            continue

        economic_signal_id = str(
            row.get("economic_signal_id") or ""
        ).strip()

        if economic_signal_id:
            consumed.add(economic_signal_id)

    return consumed


def filled_sell_exit_intent_ids(
    fills_path=FILLS_PATH,
) -> set:
    """
    Durable cross-plan SELL intent-consumption authority.

    Legacy SELL fills without exit_intent_id are grandfathered.
    New successful SELL fills carrying exit_intent_id consume that
    economic exit intent permanently in the immutable fill journal.
    """
    consumed = set()

    for row in load_fill_journal_strict(fills_path):
        if (
            str(row.get("side") or "").upper()
            != "SELL"
        ):
            continue

        exit_intent_id = str(
            row.get("exit_intent_id") or ""
        ).strip()

        if exit_intent_id:
            consumed.add(exit_intent_id)

    return consumed


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
    Fail-closed execution-plan freshness guard.

    Missing/malformed timestamps, invalid max-age configuration,
    non-positive max-age, and future timestamps are rejected.
    """
    try:
        import os
        from datetime import datetime, timezone, timedelta

        raw_max_age = os.getenv(
            "NSC_EQU_PLAN_MAX_AGE_MIN",
            "",
        ).strip()

        max_age_min = (
            int(raw_max_age)
            if raw_max_age
            else 180
        )

        if max_age_min <= 0:
            return True

        ts = (
            plan.get("ts")
            or plan.get("generated_at")
            or plan.get("created_at")
        )

        if not ts:
            return True

        dt = _parse_iso_ts(ts)

        if dt is None:
            return True

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age = now - dt

        if age < timedelta(0):
            return True

        return age > timedelta(
            minutes=max_age_min
        )

    except Exception:
        return True

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

        # Stale plan guard must run before rollover so an invalid,
        # expired, or future-dated plan cannot mutate idempotence state.
        if _is_plan_stale(plan):
            payload = {"ts": utc_now_iso(), "plan_id": plan_id, "fills_created": 0, "status": "SKIPPED_STALE_PLAN"}
            _set_last_broker_run(store, state, payload)
            store.save(state)
            print({"plan_id": plan_id, "policy": policy, "fills_created": 0, "status": "SKIPPED_STALE_PLAN"})
            return

        # Only an admitted fresh plan may roll execution state forward.
        _ensure_plan_rollover(state, plan_id)


        # The immutable fill journal is the durable execution
        # authority. Derived positions are repaired from it before
        # any new order can be processed.
        positions, positions_repaired = (
            reconcile_positions_from_fill_journal(
                FILLS_PATH,
                POSITIONS_PATH,
            )
        )

        # Idempotence is durable across plan rollover/restart.
        # StateStore remains an additional same-run/cache guard only.
        durable_seen = durable_filled_order_ids(FILLS_PATH)
        seen = _get_orders_seen(store, state) | durable_seen

        governance_path = (
            ROOT
            / "equities_offensive/governance/"
            "governance_engine_pro.json"
        )
        try:
            governance_doc = json.loads(
                governance_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise RuntimeError(
                "capacity_governance_unavailable:"
                f"{type(exc).__name__}:{exc}"
            ) from exc

        if not isinstance(governance_doc, dict):
            raise RuntimeError(
                "capacity_governance_invalid_document"
            )

        capacity_contract = build_capacity_contract(
            governance=governance_doc,
            scope="equities_offensive",
            root=ROOT,
        )
        admitted_new_entries = 0
        admitted_buy_notional = 0.0
        admitted_buy_notional_by_asset = {}

        # In preprod we expect SIMULATED_ONLY (orders likely empty),
        # but we still support simulated fills if orders exist.
        created = 0

        REJECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
        REJECTED_PATH.touch(exist_ok=True)

        # Durable authority for economic BUY idempotence.
        # This is reconstructed from immutable FILLED events
        # rather than relying only on transient StateStore data.
        consumed_buy_signal_ids = (
            filled_buy_economic_signal_ids(
                FILLS_PATH
            )
        )

        consumed_sell_exit_intent_ids = (
            filled_sell_exit_intent_ids(
                FILLS_PATH
            )
        )

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

            economic_signal_id = str(
                o.get("economic_signal_id") or ""
            ).strip()

            market_bar_id = str(
                o.get("market_bar_id") or ""
            ).strip()

            market_bar_date = str(
                o.get("market_bar_date") or ""
            ).strip()

            timeframe = str(
                o.get("timeframe") or ""
            ).strip()

            exit_intent_id = str(
                o.get("exit_intent_id") or ""
            ).strip()

            # Economic idempotence applies to BUY signals and
            # SELL exit intents independently.
            #
            # Every BUY must carry the complete economic identity
            # contract. Missing provenance fails closed before any
            # order/fill identity is created.
            #
            # SELL semantics remain independent.
            if side == "BUY":
                missing_identity_fields = [
                    name
                    for name, value in (
                        (
                            "economic_signal_id",
                            economic_signal_id,
                        ),
                        (
                            "market_bar_id",
                            market_bar_id,
                        ),
                        (
                            "market_bar_date",
                            market_bar_date,
                        ),
                        (
                            "timeframe",
                            timeframe,
                        ),
                    )
                    if not value
                ]

                if missing_identity_fields:
                    append_jsonl(
                        REJECTED_PATH,
                        {
                            "ts": utc_now_iso(),
                            "engine": (
                                "simulated_broker_v1"
                            ),
                            "plan_id": plan_id,
                            "policy": policy,
                            "status": "REJECTED",
                            "reason": (
                                "missing_economic_signal_identity"
                            ),
                            "symbol": symbol,
                            "side": side,
                            "missing_identity_fields": (
                                missing_identity_fields
                            ),
                            "order": o,
                        },
                    )
                    continue

            if (
                side == "SELL"
                and not exit_intent_id
            ):
                append_jsonl(
                    REJECTED_PATH,
                    {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": (
                            "missing_exit_intent_identity"
                        ),
                        "symbol": symbol,
                        "side": side,
                        "order": o,
                    },
                )
                continue

            if (
                side == "SELL"
                and exit_intent_id
                in consumed_sell_exit_intent_ids
            ):
                append_jsonl(
                    REJECTED_PATH,
                    {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": (
                            "exit_intent_already_consumed"
                        ),
                        "symbol": symbol,
                        "side": side,
                        "exit_intent_id": exit_intent_id,
                        "order": o,
                    },
                )
                continue

            if (
                side == "BUY"
                and economic_signal_id
                in consumed_buy_signal_ids
            ):
                append_jsonl(
                    REJECTED_PATH,
                    {
                        "ts": utc_now_iso(),
                        "engine": (
                            "simulated_broker_v1"
                        ),
                        "plan_id": plan_id,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": (
                            "economic_signal_already_consumed"
                        ),
                        "symbol": symbol,
                        "side": side,
                        "economic_signal_id": (
                            economic_signal_id
                        ),
                        "market_bar_id": (
                            market_bar_id or None
                        ),
                        "market_bar_date": (
                            market_bar_date or None
                        ),
                        "timeframe": (
                            timeframe or None
                        ),
                        "order": o,
                    },
                )
                continue

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
            # Missing market data must fail closed: never fabricate a fill price.
            price = get_price(symbol, fallback=0.0)

            if price <= 0:
                append_jsonl(
                    REJECTED_PATH,
                    {
                        "ts": utc_now_iso(),
                        "engine": "simulated_broker_v1",
                        "plan_id": plan_id,
                        "order_id": oid,
                        "policy": policy,
                        "status": "REJECTED",
                        "reason": "market_price_unavailable",
                        "symbol": symbol,
                        "side": side,
                        "requested_qty": requested_qty,
                        "effective_qty": effective_qty,
                        "order": o,
                    },
                )
                _mark_order_seen(store, state, oid)
                continue

            if side == "BUY":
                admission = admit_buy(
                    contract=capacity_contract,
                    positions=positions,
                    symbol=symbol,
                    qty=effective_qty,
                    price=price,
                    new_entries_used=admitted_new_entries,
                    buy_notional_used=admitted_buy_notional,
                    buy_notional_by_asset_used=admitted_buy_notional_by_asset.get(symbol, 0.0),
                    price_resolver=get_price,
                )

                if not admission.allowed:
                    append_jsonl(
                        REJECTED_PATH,
                        {
                            "ts": utc_now_iso(),
                            "order_id": oid,
                            "symbol": symbol,
                            "side": side,
                            "requested_qty": requested_qty,
                            "effective_qty": effective_qty,
                            "price": price,
                            "reason": (
                                "capacity_rejected:"
                                f"{admission.reason}"
                            ),
                        },
                    )
                    continue


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

            # Preserve economic provenance on the immutable
            # execution event. Legacy orders may legitimately
            # omit these fields until strict cutover.
            if economic_signal_id:
                fill["economic_signal_id"] = (
                    economic_signal_id
                )

            if market_bar_id:
                fill["market_bar_id"] = (
                    market_bar_id
                )

            if market_bar_date:
                fill["market_bar_date"] = (
                    market_bar_date
                )

            if timeframe:
                fill["timeframe"] = timeframe

            if exit_intent_id:
                fill["exit_intent_id"] = (
                    exit_intent_id
                )

            if quantity_adjustment is not None:
                fill["quantity_adjustment"] = quantity_adjustment

            append_jsonl(FILLS_PATH, fill)
            if side == "BUY":
                if admission.is_new_position:
                    admitted_new_entries += 1
                admitted_buy_notional += admission.order_notional_usd
                admitted_buy_notional_by_asset[symbol] = admitted_buy_notional_by_asset.get(symbol, 0.0) + admission.order_notional_usd

            # The durable journal is authoritative. Update the local
            # idempotency sets immediately after the durable append so
            # an identical order later in the same process cannot fill
            # twice even before StateStore persistence.
            durable_seen.add(oid)
            seen.add(oid)

            # Same-process protection if multiple orders in one
            # plan unexpectedly carry the same economic signal.
            if (
                side == "BUY"
                and economic_signal_id
            ):
                consumed_buy_signal_ids.add(
                    economic_signal_id
                )

            if (
                side == "SELL"
                and exit_intent_id
            ):
                consumed_sell_exit_intent_ids.add(
                    exit_intent_id
                )

            apply_fill(
                positions,
                symbol,
                side,
                effective_qty,
                price,
            )

            _mark_order_seen(store, state, oid)
            created += 1

        # positions.json is the broker-derived snapshot.
        # exposure_snapshot.json has a single canonical writer:
        # execution/position_tracker.py, which runs immediately after
        # the broker in run_equities_pipeline.py.
        save_positions(positions)

        _set_last_broker_run(
            store,
            state,
            {
                "ts": utc_now_iso(),
                "plan_id": plan_id,
                "fills_created": created,
                "positions_repaired": positions_repaired,
            },
        )
        store.save(state)

        print(json.dumps({"plan_id": plan_id, "policy": policy, "fills_created": created}, ensure_ascii=False, indent=2))

    finally:
        store.close()

if __name__ == "__main__":
    main()
