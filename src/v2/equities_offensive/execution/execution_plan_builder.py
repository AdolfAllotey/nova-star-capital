#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.equities_offensive.core.state_store import StateStore

OUT_PATH = Path("data/equities_offensive/execution/execution_plan.json")

CANDIDATES_PATH = Path("data/equities_offensive/risk/candidates.json")
GOV_PATH = Path("data/governance/governance_engine_pro.json")
TRADING_WINDOW_PATH = Path("data/ops/trading_window.json")

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

def sha16(obj: Any) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def normalize_action_policy(gov: Dict[str, Any]) -> str:
    # Source unique "king"
    # Expected fields could vary; we normalize safely.
    mode = (gov.get("mode") or gov.get("state") or "").upper()
    policy = (gov.get("action_policy") or gov.get("policy") or "").upper()

    # Hard defaults (PREPROD safe)
    if policy in {"SIMULATED_ONLY", "EXIT_ONLY", "LIVE"}:
        return policy

    # fallback from mode keywords
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

def build_orders_from_candidates(cands: Dict[str, Any], action_policy: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    candidates.json expected shape:
      { "ts":..., "candidates":[ {symbol, side, qty, limit_price?, reason?, score? } ... ] }
    We produce candidate_orders list always; and orders list depending on policy.
    """
    reasons: List[str] = []
    candidates = cands.get("candidates") if isinstance(cands, dict) else None
    if not isinstance(candidates, list):
        return [], ["candidates missing or invalid"]

    # normalize
    cand_orders: List[Dict[str, Any]] = []
    for c in candidates:
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

        cand_orders.append({
            "symbol": sym,
            "side": side,
            "qty": qty,
            "type": c.get("type", "MKT"),
            "limit_price": c.get("limit_price"),
            "score": c.get("score"),
            "reason": c.get("reason"),
            "risk_notes": c.get("risk_notes"),
        })

    if not cand_orders:
        return [], ["no valid candidates"]

    # By policy:
    if action_policy == "SIMULATED_ONLY":
        reasons.append("policy=SIMULATED_ONLY => orders=[] (candidates kept)")
        return cand_orders, reasons
    if action_policy == "EXIT_ONLY":
        exit_orders = [o for o in cand_orders if o["side"] == "SELL"]
        reasons.append(f"policy=EXIT_ONLY => orders=SELL only ({len(exit_orders)})")
        return cand_orders, reasons
    # LIVE
    reasons.append(f"policy=LIVE => orders=candidates ({len(cand_orders)})")
    return cand_orders, reasons

def build_plan_id(inputs: Dict[str, Any]) -> str:
    return f"plan_{utc_now_iso().replace(':','').replace('-','').replace('.','')}_{sha16(inputs)}"

def main():
    store = StateStore()
    store.with_lock()
    try:
        state = store.load()

        gov = load_json(GOV_PATH, default={}) or {}
        action_policy = normalize_action_policy(gov)

        gate_ok, gate_reasons = gate_trading_window()
        if not gate_ok:
            # Even if blocked, we still emit a plan for observability (orders empty)
            action_policy_effective = "SIMULATED_ONLY"
        else:
            action_policy_effective = action_policy

        cands = load_json(CANDIDATES_PATH, default={}) or {}
        inputs = {
            "candidates_path": str(CANDIDATES_PATH),
            "candidates_hash": sha16(cands),
            "gov_hash": sha16(gov),
            "trading_window_hash": sha16(load_json(TRADING_WINDOW_PATH, default={}) or {}),
            "action_policy": action_policy_effective,
        }
        plan_id = build_plan_id(inputs)

        # idempotence: if already seen, do not re-emit new orders
        if store.has_seen_plan(state, plan_id):
            out = {
                "ts": utc_now_iso(),
                "engine": "execution_plan_builder_v1",
                "plan_id": plan_id,
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

        cand_orders, order_reasons = build_orders_from_candidates(cands, action_policy_effective)

        # If trading window blocked -> force no orders
        orders: List[Dict[str, Any]] = []
        reasons = []
        reasons.extend(gate_reasons)
        reasons.extend(order_reasons)

        if gate_ok:
            # apply policy-built orders
            if action_policy_effective == "LIVE":
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

        # mark seen AFTER writing plan (still idempotent for next run)
        store.mark_plan_seen(state, plan_id)
        store.set_last_run(state, plan_id, inputs)
        store.save(state)

        save_json(OUT_PATH, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))

    finally:
        store.close()

if __name__ == "__main__":
    main()
