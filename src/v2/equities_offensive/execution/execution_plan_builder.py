#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.equities_offensive.position_sizer import size_qty_from_budget

from src.v2.equities_offensive.core.state_store import StateStore

def data_root() -> Path:
    return Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

ROOT = data_root()
OUT_PATH = ROOT / "equities_offensive/execution/execution_plan.json"

ENTRY_CANDIDATES_PATH = ROOT / "equities_offensive/risk/execution_candidates.json"
EXIT_CANDIDATES_PATH = ROOT / "equities_offensive/risk/exit_candidates.json"
LEGACY_CANDIDATES_PATH = ROOT / "equities_offensive/risk/candidates.json"

GOV_PATH = ROOT / "equities_offensive/governance/governance_engine_pro.json"
TRADING_WINDOW_PATH = ROOT / "equities_offensive/ops/trading_window.json"
POSITIONS_PATH = ROOT / "equities_offensive/state/positions.json"
FILLS_PATH = ROOT / "equities_offensive/execution/simulated_fills.jsonl"
PRICES_PATH = ROOT / "equities_offensive/market/prices.json"
PORTFOLIO_INPUT_PATH = ROOT / "portfolio/inputs/equities_offensive_portfolio_input.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


VOLATILE_IDENTITY_KEYS = {
    "ts",
    "timestamp",
    "generated_at",
    "updated_at",
    "fetched_at",
    "synced_at",
    "source_timestamp",
    "run_id",
    "plan_id",
}


def normalize_identity_payload(obj: Any) -> Any:
    """
    Produit une représentation métier déterministe.

    Les métadonnées purement techniques et horodatées sont retirées
    récursivement avant le calcul de l'identité du plan.
    """
    if isinstance(obj, dict):
        normalized = {}

        for key, value in sorted(
            obj.items(),
            key=lambda item: str(item[0]),
        ):
            normalized_key = str(key)

            if (
                normalized_key.lower()
                in VOLATILE_IDENTITY_KEYS
            ):
                continue

            normalized[normalized_key] = (
                normalize_identity_payload(value)
            )

        return normalized

    if isinstance(obj, list):
        normalized_items = [
            normalize_identity_payload(item)
            for item in obj
        ]

        if all(
            isinstance(item, dict)
            for item in normalized_items
        ):
            return sorted(
                normalized_items,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )

        return normalized_items

    return obj


def sha16(obj: Any) -> str:
    normalized = normalize_identity_payload(obj)

    serialized = json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:16]


def normalize_action_policy(gov: Dict[str, Any]) -> str:
    env_policy = (os.getenv("NSC_EQU_ACTION_POLICY") or "").upper().strip()
    if env_policy in {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "EXIT_ONLY", "LIVE"}:
        return env_policy

    mode = (gov.get("mode") or gov.get("state") or "").upper()
    policy = (gov.get("action_policy") or gov.get("policy") or "").upper()

    if policy in {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "EXIT_ONLY", "LIVE"}:
        return policy

    if "PREPROD" in mode or "SIM" in mode:
        return "SIMULATED_ONLY"
    if "EXIT" in mode:
        return "EXIT_ONLY"
    if "PROD" in mode or "LIVE" in mode:
        return "LIVE"
    return "SIMULATED_ONLY"


def gate_trading_window() -> Tuple[bool, List[str]]:
    doc = load_json(TRADING_WINDOW_PATH, default=None)
    if not isinstance(doc, dict):
        return False, ["missing trading_window.json"]
    allowed = bool(doc.get("allowed", False))
    reasons = doc.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    if not allowed:
        return False, ["trading window blocked"] + [str(x) for x in reasons]
    return True, ["trading window allowed"]


def parse_ts(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def load_portfolio_input() -> Dict[str, Any]:
    doc = load_json(PORTFOLIO_INPUT_PATH, default={}) or {}
    return doc if isinstance(doc, dict) else {}

def load_positions() -> Dict[str, Dict[str, Any]]:
    positions = load_json(POSITIONS_PATH, default={}) or {}
    return positions if isinstance(positions, dict) else {}


def get_market_price(symbol: str, fallback: float = 0.0) -> float:
    doc = load_json(PRICES_PATH, default={}) or {}
    if isinstance(doc, dict):
        prices = doc.get("prices") if isinstance(doc.get("prices"), dict) else doc
        try:
            px = prices.get(str(symbol).upper())
            if px is not None:
                return float(px)
        except Exception:
            pass
    return float(fallback)


def get_trailing_pct_for_regime(regime: str) -> float:
    regime = str(regime or "risk_on").lower()
    if regime in {"risk_off", "risk_off_blocked"}:
        return 0.05
    if regime in {"balanced", "neutral"}:
        return 0.08
    return 0.12

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def last_sell_times_by_symbol() -> Dict[str, datetime]:
    fills = read_jsonl(FILLS_PATH)
    out: Dict[str, datetime] = {}
    for f in fills:
        symbol = f.get("symbol")
        side = (f.get("side") or "").upper()
        status = (f.get("status") or "").upper()
        if not symbol or side != "SELL" or status != "FILLED":
            continue
        ts = parse_ts(f.get("ts"))
        if ts is None:
            continue
        prev = out.get(symbol)
        if prev is None or ts > prev:
            out[symbol] = ts
    return out


def get_reentry_cooldown_minutes() -> int:
    raw = os.getenv("NSC_EQU_REENTRY_COOLDOWN_MIN", "720").strip()
    try:
        val = int(raw)
    except Exception:
        val = 720
    return max(val, 0)


def convert_entry_candidate(c: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Convert a Risk Engine candidate into an unsized BUY order.

    Quantity is deliberately not created here. The canonical monetary
    contract is size_usd, generated by the Risk Engine. Quantity is derived
    later from the current market price through position_sizer.py.
    """
    symbol = str(c.get("symbol") or "").strip().upper()

    if not symbol:
        return None

    try:
        size_usd = float(c.get("size_usd") or 0.0)
    except Exception:
        size_usd = 0.0

    return {
        "symbol": symbol,
        "side": "BUY",
        "qty": None,
        "type": "MKT",
        "limit_price": None,
        "score": c.get("meta_score") or c.get("score"),
        "reason": (
            c.get("setup")
            or c.get("reason")
            or "entry_signal"
        ),
        "risk_notes": c.get("risk_notes"),
        "size_usd": round(size_usd, 2),
        "budget": c.get("budget"),
        "fx": c.get("fx"),
        "risk_meta": c.get("meta"),
    }


def size_entry_candidate(
    candidate: Dict[str, Any],
    caps: Dict[str, Any],
) -> Tuple[Dict[str, Any] | None, str | None]:
    """
    Derive an actionable integer share quantity from Risk size_usd.

    Returns:
        (sized_order, rejection_reason)
    """
    symbol = str(
        candidate.get("symbol") or ""
    ).strip().upper()

    try:
        size_usd = float(
            candidate.get("size_usd") or 0.0
        )
    except Exception:
        size_usd = 0.0

    if not symbol:
        return None, "BUY sizing rejected: missing_symbol"

    if size_usd <= 0:
        return (
            None,
            f"skip {symbol} BUY invalid_size_usd="
            f"{size_usd}",
        )

    price = get_market_price(
        symbol,
        fallback=0.0,
    )

    if price <= 0:
        return (
            None,
            f"skip {symbol} BUY missing_live_price",
        )

    qty_requested = size_usd / price

    broker_capabilities = {
        "broker_id": "simulated_ibkr",
        "asset_class": "equity",
        "fractional_quantity": True,
        "quantity_step": 0.000001,
        "minimum_quantity": 0.000001,
        "minimum_notional_usd": 1.0,
    }

    sizing_result = size_qty_from_budget(
        size_usd=size_usd,
        price=price,
        caps=caps,
        min_notional_usd=50.0,
        broker_capabilities=broker_capabilities,
    )

    sizing = {
        "engine": "position_sizer_v1.1",
        "broker_id": broker_capabilities["broker_id"],
        "asset_class": broker_capabilities["asset_class"],
        "fractional_quantity": broker_capabilities[
            "fractional_quantity"
        ],
        "share_policy": sizing_result.policy,
        "quantity_step": sizing_result.quantity_step,
        "requested_size_usd": round(
            size_usd,
            2,
        ),
        "price_used_usd": round(
            price,
            8,
        ),
        "qty_requested": round(
            qty_requested,
            8,
        ),
        "qty_selected": round(
            float(sizing_result.qty),
            8,
        ),
        "notional_selected_usd": round(
            float(sizing_result.notional),
            2,
        ),
        "min_notional_usd": 50.0,
        "max_order_notional_usd": (
            caps.get("max_order_notional_usd")
            if isinstance(caps, dict)
            else None
        ),
        "warnings": list(
            sizing_result.warnings or []
        ),
    }

    if sizing_result.qty <= 0:
        warning_text = ",".join(
            sizing_result.warnings or []
        ) or "non_actionable_quantity"

        return (
            None,
            f"skip {symbol} BUY sizing_rejected "
            f"size_usd={size_usd:.2f} "
            f"price={price:.8f} "
            f"qty_requested={qty_requested:.8f} "
            f"warnings={warning_text}",
        )

    sized = dict(candidate)

    sized.update(
        {
            "symbol": symbol,
            "qty": float(sizing_result.qty),
            "price": round(price, 8),
            "size_usd": round(size_usd, 2),
            "qty_requested": round(
                qty_requested,
                8,
            ),
            "notional_usd": round(
                float(sizing_result.notional),
                2,
            ),
            "sizing": sizing,
        }
    )

    return sized, None


def convert_exit_candidate(c: Dict[str, Any]) -> Dict[str, Any] | None:
    symbol = c.get("symbol")
    side = (c.get("side") or "SELL").upper()
    qty = c.get("qty", 0)
    if not symbol or side != "SELL":
        return None
    try:
        qty = float(qty)
    except Exception:
        return None
    if qty <= 0:
        return None
    return {
        "symbol": symbol,
        "side": "SELL",
        "qty": qty,
        "type": c.get("type", "MKT"),
        "limit_price": c.get("limit_price"),
        "score": c.get("score"),
        "reason": c.get("reason") or "exit_signal",
        "risk_notes": c.get("risk_notes"),
    }


def load_merged_candidates() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    entry_doc = load_json(ENTRY_CANDIDATES_PATH, default={}) or {}
    exit_doc = load_json(EXIT_CANDIDATES_PATH, default={}) or {}
    legacy_doc = load_json(LEGACY_CANDIDATES_PATH, default={}) or {}

    merged: List[Dict[str, Any]] = []

    entry_candidates = entry_doc.get("candidates") if isinstance(entry_doc, dict) else None
    if isinstance(entry_candidates, list) and entry_candidates:
        for c in entry_candidates:
            if isinstance(c, dict):
                o = convert_entry_candidate(c)
                if o:
                    merged.append(o)

    exit_candidates = exit_doc.get("candidates") if isinstance(exit_doc, dict) else None
    if isinstance(exit_candidates, list) and exit_candidates:
        for c in exit_candidates:
            if isinstance(c, dict):
                o = convert_exit_candidate(c)
                if o:
                    merged.append(o)

    if not merged:
        legacy_candidates = legacy_doc.get("candidates") if isinstance(legacy_doc, dict) else None
        if isinstance(legacy_candidates, list):
            for c in legacy_candidates:
                if not isinstance(c, dict):
                    continue
                sym = c.get("symbol")
                side = (c.get("side") or "").upper()
                qty = c.get("qty")
                if not sym or side not in {"BUY", "SELL"}:
                    continue
                try:
                    qty = float(qty)
                except Exception:
                    continue
                if qty <= 0:
                    continue
                merged.append({
                    "symbol": sym,
                    "side": side,
                    "qty": qty,
                    "type": c.get("type", "MKT"),
                    "limit_price": c.get("limit_price"),
                    "score": c.get("score"),
                    "reason": c.get("reason"),
                    "risk_notes": c.get("risk_notes"),
                })

    merged_doc = {"ts": utc_now_iso(), "candidates": merged}
    return entry_doc, exit_doc, legacy_doc, merged_doc



def dedupe_exit_orders(orders):
    """
    Keep only one SELL order per symbol.
    Priority: trailing_stop_hit > stop_loss > other.
    """
    priority = {
        "trailing_stop_hit": 3,
        "stop_loss": 2,
    }

    kept = {}
    for o in orders:
        if not isinstance(o, dict):
            continue
        if str(o.get("side", "")).upper() != "SELL":
            key = f"NON_SELL_{len(kept)}_{o.get('symbol')}"
            kept[key] = o
            continue

        sym = str(o.get("symbol", "")).upper()
        reason = str(o.get("reason", ""))
        score = 0
        for k, v in priority.items():
            if k in reason:
                score = v
                break

        prev = kept.get(sym)
        if prev is None:
            kept[sym] = o
        else:
            prev_reason = str(prev.get("reason", ""))
            prev_score = 0
            for k, v in priority.items():
                if k in prev_reason:
                    prev_score = v
                    break
            if score > prev_score:
                kept[sym] = o

    return list(kept.values())


def build_orders_from_candidates(cands: Dict[str, Any], action_policy: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    reasons: List[str] = []
    candidates = cands.get("candidates") if isinstance(cands, dict) else None
    if not isinstance(candidates, list):
        return [], ["candidates missing or invalid"]

    positions = load_positions()
    portfolio_input = load_portfolio_input()
    portfolio_regime = str(
        portfolio_input.get("regime", "risk_on")
    ).lower()
    trailing_pct = get_trailing_pct_for_regime(
        portfolio_regime
    )

    governance = load_json(
        GOV_PATH,
        default={},
    ) or {}

    governance_caps = (
        governance.get("caps")
        if isinstance(governance, dict)
        else {}
    )

    if not isinstance(governance_caps, dict):
        governance_caps = {}

    sell_last_ts = last_sell_times_by_symbol()
    cooldown_min = get_reentry_cooldown_minutes()
    now = datetime.now(timezone.utc)

    cand_orders: List[Dict[str, Any]] = []

    # Auto trailing-stop exits
    for sym, pos in positions.items():
        try:
            qty = float(pos.get("qty", 0.0) or 0.0)
            avg_price = float(pos.get("avg_price", 0.0) or 0.0)
        except Exception:
            continue

        if qty <= 0 or avg_price <= 0:
            continue

        current_price = get_market_price(sym, fallback=avg_price)
        if current_price <= 0:
            continue

        trailing_stop_price = current_price * (1.0 - trailing_pct)
        # Actionable only if current price has already fallen at or below a stop based on avg anchor
        anchored_stop = avg_price * (1.0 - trailing_pct)

        if current_price <= anchored_stop:
            cand_orders.append({
                "symbol": sym,
                "side": "SELL",
                "qty": qty,
                "type": "MKT",
                "limit_price": None,
                "score": 1.0,
                "reason": "trailing_stop_hit",
                "risk_notes": f"regime={portfolio_regime}; trailing_pct={round(trailing_pct,4)}; stop={round(anchored_stop,4)}; price={round(current_price,4)}",
            })
            reasons.append(f"trailing stop hit for {sym} at {current_price:.4f} <= {anchored_stop:.4f}")

    for c in candidates:
        if not isinstance(c, dict):
            continue

        sym = str(
            c.get("symbol") or ""
        ).strip().upper()
        side = str(
            c.get("side") or ""
        ).upper()

        if not sym or side not in {"BUY", "SELL"}:
            continue

        if side == "BUY":
            sized_candidate, sizing_rejection = (
                size_entry_candidate(
                    c,
                    governance_caps,
                )
            )

            if sized_candidate is None:
                if sizing_rejection:
                    reasons.append(
                        sizing_rejection
                    )
                continue

            c = sized_candidate
            sym = c["symbol"]

        qty = c.get("qty")

        try:
            qty = float(qty)
        except Exception:
            reasons.append(
                f"skip {sym} {side} invalid_qty="
                f"{qty!r}"
            )
            continue

        if qty <= 0:
            reasons.append(
                f"skip {sym} {side} qty<=0"
            )
            continue

        existing = positions.get(sym) if isinstance(positions.get(sym), dict) else {}
        existing_qty = existing.get("qty", 0) if isinstance(existing, dict) else 0
        try:
            existing_qty = float(existing_qty)
        except Exception:
            existing_qty = 0.0

        if side == "BUY" and existing_qty > 0:
            # Production-grade PREPROD behavior:
            # A valid BUY signal on an already-open position should not be ignored.
            # It becomes a progressive reinforcement order, capped to avoid overreaction.
            # Cap rule: add at most 50% of the current position quantity per cycle.
            # Production-grade sleeve target guard:
            # Source of truth = master portfolio_state, not stale portfolio input.
            portfolio_state = load_json(ROOT / "portfolio/state/portfolio_state.json", default={}) or {}
            try:
                offensive_state = ((portfolio_state.get("bricks") or {}).get("equities_offensive") or {})
            except Exception:
                offensive_state = {}

            try:
                current_exposure = float(offensive_state.get("current_exposure_eur") or 0.0)
            except Exception:
                current_exposure = 0.0

            try:
                target_exposure = float(offensive_state.get("target_amount_eur") or 0.0)
            except Exception:
                target_exposure = 0.0

            # Fallback from live positions if portfolio_state is missing/stale.
            if current_exposure <= 0:
                try:
                    current_exposure = sum(
                        float(pv.get("qty", 0.0) or 0.0)
                        * get_market_price(sym_key, fallback=float(pv.get("avg_price", 0.0) or 0.0))
                        for sym_key, pv in positions.items()
                        if isinstance(pv, dict)
                    )
                except Exception:
                    current_exposure = 0.0

            if target_exposure > 0 and current_exposure >= target_exposure:
                reasons.append(
                    f"skip {sym} BUY reinforcement sleeve_at_or_above_target "
                    f"current={round(current_exposure,2)} target={round(target_exposure,2)}"
                )
                continue

            max_reinforce_qty = existing_qty * 0.50
            reinforce_qty = min(qty, max_reinforce_qty)

            if target_exposure > 0 and current_exposure > 0:
                px = get_market_price(sym, fallback=0.0)
                remaining_gap = max(0.0, target_exposure - current_exposure)
                if px > 0:
                    reinforce_qty = min(reinforce_qty, remaining_gap / px)

            if reinforce_qty <= 0:
                reasons.append(f"skip {sym} BUY already in position qty={existing_qty} reinforce_qty<=0")
                continue

            qty = reinforce_qty
            reasons.append(
                f"reinforce {sym} BUY already in position qty={existing_qty} "
                f"requested_qty={c.get('qty')} reinforced_qty={round(qty, 6)} cap=50pct"
            )

        if side == "BUY" and cooldown_min > 0:
            last_sell_ts = sell_last_ts.get(sym)
            if last_sell_ts is not None:
                elapsed_min = (now - last_sell_ts).total_seconds() / 60.0
                if elapsed_min < cooldown_min:
                    reasons.append(
                        f"skip {sym} BUY cooldown_after_sell active "
                        f"elapsed={round(elapsed_min,1)}m < {cooldown_min}m"
                    )
                    continue

        if side == "SELL" and existing_qty <= 0:
            reasons.append(f"skip {sym} SELL no open position")
            continue

        if side == "SELL" and qty > existing_qty > 0:
            qty = existing_qty

        order = {
            "symbol": sym,
            "side": side,
            "qty": qty,
            "type": c.get("type", "MKT"),
            "limit_price": c.get("limit_price"),
            "score": c.get("score"),
            "reason": c.get("reason"),
            "risk_notes": c.get("risk_notes"),
        }

        if side == "BUY":
            order.update(
                {
                    "price": c.get("price"),
                    "size_usd": c.get("size_usd"),
                    "qty_requested": (
                        c.get("qty_requested")
                    ),
                    "notional_usd": (
                        c.get("notional_usd")
                    ),
                    "sizing": c.get("sizing"),
                    "budget": c.get("budget"),
                    "fx": c.get("fx"),
                    "risk_meta": (
                        c.get("risk_meta")
                    ),
                }
            )

        cand_orders.append(order)

    # In EXIT_ONLY, even if no explicit SELL candidate exists,
    # we must still allow smart de-risking to reduce an over-exposed sleeve.
    if not cand_orders and action_policy != "EXIT_ONLY":
        return [], ["no valid candidates after position filter"] + reasons

    if action_policy == "SIMULATED_ONLY":
        reasons.append("policy=SIMULATED_ONLY => orders=[] (candidates kept)")
        return cand_orders, reasons

    if action_policy == "EXIT_ONLY":
        exit_orders = [o for o in cand_orders if o["side"] == "SELL"]

        positions = load_positions()
        for symbol, pos in positions.items():
            try:
                qty = float(pos.get("qty", 0.0) or 0.0)
                avg_price = float(pos.get("avg_price", 0.0) or 0.0)
            except Exception:
                continue

            if qty <= 0:
                continue

            already_has_sell = any(
                o.get("symbol") == symbol and o.get("side") == "SELL"
                for o in exit_orders
            )
            if already_has_sell:
                continue

            current_price = get_market_price(symbol, fallback=avg_price if avg_price > 0 else 0.0)
            pnl_pct = 0.0
            if avg_price > 0 and current_price > 0:
                pnl_pct = (current_price - avg_price) / avg_price

            if pnl_pct > 0.03:
                reduce_ratio = 0.25
                risk_note = "smart_reduce_25pct_winner"
            elif pnl_pct < -0.03:
                reduce_ratio = 1.0
                risk_note = "smart_reduce_100pct_loser"
            else:
                reduce_ratio = 0.5
                risk_note = "smart_reduce_50pct_neutral"

            reduce_qty = round(qty * reduce_ratio, 8)
            if reduce_qty <= 0:
                continue

            exit_orders.append({
                "symbol": symbol,
                "side": "SELL",
                "qty": reduce_qty,
                "type": "MKT",
                "limit_price": None,
                "score": 1.0,
                "reason": "risk_off_smart_de_risking",
                "risk_notes": risk_note,
            })

        reasons.append(f"policy=EXIT_ONLY + smart_de-risking => SELL ({len(exit_orders)})")
        return exit_orders, reasons

    if action_policy == "SIMULATED_EXECUTION":
        max_new_entries = int(os.getenv("NSC_EQU_MAX_NEW_ENTRIES_PER_RUN", "2"))
        limited_orders = cand_orders[:max_new_entries]
        reasons.append(
            f"policy=SIMULATED_EXECUTION => orders=candidates "
            f"({len(limited_orders)}/{len(cand_orders)}, max_new_entries={max_new_entries})"
        )
        return limited_orders, reasons

    reasons.append(f"policy=LIVE => orders=candidates ({len(cand_orders)})")
    return cand_orders, reasons


def build_plan_id(inputs: Dict[str, Any]) -> str:
    """
    Identité métier stable.

    Deux exécutions portant sur les mêmes entrées métier
    doivent produire le même plan_id.
    """
    return f"plan_{sha16(inputs)}"


def build_run_id() -> str:
    """
    Identité technique unique de chaque tentative d'exécution.

    Le run_id ne participe jamais à l'idempotence métier.
    """
    compact_ts = (
        utc_now_iso()
        .replace(":", "")
        .replace("-", "")
        .replace(".", "")
    )

    return f"run_{compact_ts}"


def main():
    store = StateStore()
    store.with_lock()
    try:
        state = store.load()

        gov = load_json(GOV_PATH, default={}) or {}
        action_policy = normalize_action_policy(gov)

        gate_ok, gate_reasons = gate_trading_window()

        portfolio_input = load_portfolio_input()
        portfolio_target_weight = float(portfolio_input.get("target_weight", 0.0) or 0.0)
        portfolio_regime = str(portfolio_input.get("regime", "unknown")).lower()

        is_risk_off = (
            portfolio_target_weight <= 0.0
            or portfolio_regime in {"risk_off", "risk_off_blocked"}
        )

        action_policy_effective = action_policy if gate_ok else "SIMULATED_ONLY"
        if is_risk_off:
            action_policy_effective = "EXIT_ONLY" if gate_ok else "SIMULATED_ONLY"

        entry_doc, exit_doc, legacy_doc, merged_doc = load_merged_candidates()

        current_positions = load_json(
            POSITIONS_PATH,
            default={}
        ) or {}

        inputs = {
            "entry_candidates_path": str(ENTRY_CANDIDATES_PATH),
            "entry_candidates_hash": sha16(entry_doc),
            "exit_candidates_path": str(EXIT_CANDIDATES_PATH),
            "exit_candidates_hash": sha16(exit_doc),
            "merged_candidates_hash": sha16(merged_doc),
            "positions_hash": sha16(current_positions),
            "prices_hash": sha16(
                load_json(
                    PRICES_PATH,
                    default={},
                ) or {}
            ),
            "gov_hash": sha16(gov),
            "trading_window_hash": sha16(
                load_json(
                    TRADING_WINDOW_PATH,
                    default={},
                ) or {}
            ),
            "action_policy": action_policy_effective,
            "portfolio_target_weight": portfolio_target_weight,
            "portfolio_regime": portfolio_regime,
        }

        if not (isinstance(entry_doc, dict) and entry_doc.get("candidates") is not None) and \
           not (isinstance(exit_doc, dict) and exit_doc.get("candidates") is not None):
            inputs["legacy_candidates_path"] = str(LEGACY_CANDIDATES_PATH)
            inputs["legacy_candidates_hash"] = sha16(legacy_doc)

        plan_id = build_plan_id(inputs)
        run_id = build_run_id()

        if store.has_seen_plan(state, plan_id):
            out = {
                "ts": utc_now_iso(),
                "engine": "execution_plan_builder_v1",
                "plan_id": plan_id,
                "run_id": run_id,
                "action_policy": action_policy_effective,
                "idempotent_skip": True,
                "candidate_orders": [],
                "orders": [],
                "reasons": ["plan already seen => skip"],
                "audit": {"inputs": inputs},
            }
            save_json(OUT_PATH, out)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return

        cand_orders, order_reasons = build_orders_from_candidates(merged_doc, action_policy_effective)

        # Guardrail: no BUY execution without live price.
        prices_doc_for_guard = load_json(PRICES_PATH, default={}) or {}
        live_prices_for_guard = prices_doc_for_guard.get("prices", {}) if isinstance(prices_doc_for_guard, dict) else {}

        filtered_orders = []
        for o in cand_orders:
            sym = str(o.get("symbol", "")).upper()
            side = str(o.get("side", "")).upper()
            if side == "BUY" and sym not in live_prices_for_guard:
                order_reasons.append(f"skip {sym} BUY missing_live_price")
                continue
            filtered_orders.append(o)

        cand_orders = filtered_orders
        cand_orders = dedupe_exit_orders(cand_orders)

        orders: List[Dict[str, Any]] = []
        reasons: List[str] = []
        reasons.extend(gate_reasons)
        if portfolio_target_weight <= 0.0 or "risk_off" in portfolio_regime:
            reasons.append(
                f"portfolio override => {action_policy_effective} (target_weight={portfolio_target_weight}, regime={portfolio_regime})"
            )
        reasons.extend(order_reasons)

        if gate_ok:
            if action_policy_effective in {"LIVE", "SIMULATED_EXECUTION"}:
                orders = cand_orders
            elif action_policy_effective == "EXIT_ONLY":
                orders = [o for o in cand_orders if o["side"] == "SELL"]
            else:
                orders = []
        else:
            orders = []
            reasons.append("market closed => orders=[]")

        out = {
            "ts": utc_now_iso(),
            "engine": "execution_plan_builder_v1",
            "plan_id": plan_id,
            "run_id": run_id,
            "action_policy": action_policy_effective,
            "idempotent_skip": False,
            "candidate_orders": cand_orders,
            "orders": orders,
            "reasons": reasons,
            "audit": {
                "inputs": inputs,
                "governance_mode": gov.get("mode") or gov.get("state"),
                "caps": gov.get("caps"),
            },
        }

        store.mark_plan_seen(state, plan_id)
        store.set_last_run(
            state,
            plan_id,
            normalize_identity_payload(inputs),
        )

        # Source de vérité de l'identité métier :
        # le suffixe du plan_id est l'empreinte normalisée
        # calculée par sha16().
        #
        # StateStore.set_last_run() utilise historiquement
        # une sérialisation JSON différente. Sans cet alignement,
        # deux empreintes peuvent différer alors que le payload
        # métier est identique.
        state.setdefault("last_run", {})
        state["last_run"]["inputs_hash"] = (
            str(plan_id).replace("plan_", "", 1)
        )

        store.save(state)

        save_json(OUT_PATH, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))

    finally:
        store.close()


if __name__ == "__main__":
    main()
