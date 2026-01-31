# -*- coding: utf-8 -*-
"""
Execution Engine Pro — SAFE / PREPROD minimal implementation.

Goal (institutional safety):
- Always write execution_plan.json (avoid stale plans).
- Enforce KING governance from data/analysis/governance_engine_pro.json at write time.
- Never allow kill_switch seeds to override KING. Keep kill_switch reasons only for observability.
- Apply caps (risk_limits) with possible override from KING.caps.
- PREPROD-friendly: can annotate orders with SIMULATED_ONLY when action_policy demands it.

This file intentionally keeps the surface-area small to avoid drift during preprod.
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("execution_engine_pro")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(x) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v) for v in x if v]
    return [str(x)]


def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _read_json(path: Path, default):
    try:
        if path.exists():
            return load_json_file(str(path))
    except Exception:
        logger.exception("[execution_engine_pro] failed to read %s", path)
    return default


def _load_data_dir() -> Path:
    # Prefer global env / existing conventions
    base = os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR")
    if base:
        return Path(base)
    # fallback: project layout (/opt/nsc/app/data)
    return Path("/opt/nsc/app/data")


def _load_king_governance(data_dir: Path) -> Tuple[Dict[str, Any], bool]:
    king_path = data_dir / "analysis" / "governance_engine_pro.json"
    king = _read_json(king_path, default={}) or {}
    if not isinstance(king, dict):
        return {}, False
    king["_king_source"] = str(king_path)
    return king, True


def _load_kill_switch(data_dir: Path) -> Dict[str, Any]:
    ks = _read_json(data_dir / "trading" / "kill_switch.json", default={}) or {}
    return ks if isinstance(ks, dict) else {}


def _derive_hard_block(king: Dict[str, Any], ks: Dict[str, Any], data_dir: Path) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    # KING hard block wins
    if bool(king.get("hard_block")):
        reasons.extend(_as_list(king.get("reasons")) or ["king_hard_block=true"])
        return True, reasons

    # kill_switch hard block (still respected), but doesn't override KING fields
    mode = str(ks.get("mode") or "normal").lower()
    hard = bool(ks.get("hard_block", False)) or (mode == "hard_block")
    enabled = bool(ks.get("enabled", False))
    if hard or enabled:
        rr = ks.get("reasons") if isinstance(ks.get("reasons"), list) else None
        if rr:
            reasons.extend(_as_list(rr))
        else:
            r = ks.get("reason")
            if r:
                reasons.append(str(r))
        if not reasons:
            reasons.append("kill_switch_hard_block=true")
        return True, reasons

    # Optional: Risk engine guard (if present)
    try:
        rs = _read_json(data_dir / "analysis" / "risk_engine_pro.json", default={}) or {}
        if isinstance(rs, dict):
            flag = str(rs.get("global_flag") or "").strip().lower()
            score = _safe_float(rs.get("score"), 0.0)
            if flag in ("risk_off", "off", "emergency") or score <= 35.0:
                reasons.append(f"auto:risk_engine={flag or 'risk_off'} score={score:.2f}")
                return True, reasons
    except Exception:
        logger.exception("[execution_engine_pro] risk_engine_pro guard failed")

    return False, []


def _apply_caps(orders: List[Dict[str, Any]], data_dir: Path, king: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rl = _read_json(data_dir / "trading" / "risk_limits.json", default={}) or {}
    if not isinstance(rl, dict):
        rl = {}

    max_orders = int(_safe_float(rl.get("max_orders_per_run", 0), 0))
    max_notional_run = _safe_float(rl.get("max_notional_eur_per_run", 0.0), 0.0)
    max_notional_asset = _safe_float(rl.get("max_notional_eur_per_asset", 0.0), 0.0)

    # KING can override caps
    kc = king.get("caps") if isinstance(king, dict) else None
    if isinstance(kc, dict) and kc:
        max_orders = int(_safe_float(kc.get("max_orders_per_run", max_orders), max_orders))
        max_notional_run = _safe_float(kc.get("max_notional_eur_per_run", max_notional_run), max_notional_run)
        max_notional_asset = _safe_float(kc.get("max_notional_eur_per_asset", max_notional_asset), max_notional_asset)

    # If max_orders == 0 => no cap
    kept: List[Dict[str, Any]] = []
    dropped_orders: List[Dict[str, Any]] = []

    total_notional = 0.0
    by_asset: Dict[str, float] = {}

    def est_notional(o: Dict[str, Any]) -> float:
        if not isinstance(o, dict):
            return 0.0
        n = o.get("notional_eur")
        if n is not None:
            return _safe_float(n, 0.0)
        # If notional missing, attempt basic estimate from capital_per_trade + weight
        cap = _read_json(data_dir / "trading" / "capital_allocation.json", default={}) or {}
        cpt = _safe_float((cap or {}).get("capital_per_trade"), 0.0)
        w = _safe_float(o.get("weight") or o.get("requested_weight") or 0.0, 0.0)
        if cpt > 0 and w > 0:
            return cpt * w
        return 0.0

    for idx, o in enumerate(orders or []):
        if not isinstance(o, dict):
            continue

        sym = (o.get("symbol") or o.get("asset") or "").lower()
        n = est_notional(o)

        # max_orders
        if max_orders > 0 and len(kept) >= max_orders:
            dropped_orders.append({"index": idx, "reason": "cap:max_orders_per_run", "order": o})
            continue

        # max_notional_run
        if max_notional_run > 0 and (total_notional + n) > max_notional_run:
            dropped_orders.append({"index": idx, "reason": "cap:max_notional_eur_per_run", "order": o, "notional_eur": n})
            continue

        # max_notional_asset
        if max_notional_asset > 0 and sym:
            prev = by_asset.get(sym, 0.0)
            if (prev + n) > max_notional_asset:
                dropped_orders.append({"index": idx, "reason": "cap:max_notional_eur_per_asset", "order": o, "notional_eur": n})
                continue

        kept.append(o)
        total_notional += n
        if sym:
            by_asset[sym] = by_asset.get(sym, 0.0) + n

    meta = {
        "caps": {
            "max_orders_per_run": max_orders,
            "max_notional_eur_per_run": max_notional_run,
            "max_notional_eur_per_asset": max_notional_asset,
        },
        "kept": len(kept),
        "dropped": len(dropped_orders),
        "total_notional_eur_est": float(total_notional),
        "notional_by_asset_est": dict(by_asset),
        "dropped_orders": dropped_orders,
    }
    return kept, meta


def _annotate_action_policy(orders: List[Dict[str, Any]], king: Dict[str, Any]) -> None:
    action_policy = king.get("action_policy")
    if action_policy == "SIMULATED_ONLY":
        for o in orders:
            if not isinstance(o, dict):
                continue
            o["action"] = "SIMULATED_ONLY"
            o.setdefault("blocked_by", [])
            if isinstance(o["blocked_by"], list) and "soft_veto:simulated_only" not in o["blocked_by"]:
                o["blocked_by"].append("soft_veto:simulated_only")


def main() -> int:
    data_dir = _load_data_dir()
    trading_dir = data_dir / "trading"
    analysis_dir = data_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    env = str(os.getenv("NSC_ENV", "PREPROD")).upper()
    now_iso = _now_iso()

    execution_plan_path = str(trading_dir / "execution_plan.json")
    execution_plan_sim_path = str(trading_dir / "execution_plan_simulated.json")
    engine_state_path = str(analysis_dir / "execution_engine_pro.json")

    # Load signals
    sized_path = trading_dir / "sized_signals.json"
    sized = _read_json(sized_path, default=[]) or []
    if not isinstance(sized, list):
        sized = []
    logger.info("[execution_engine_pro] DATA_DIR=%s", data_dir)
    logger.info("[execution_engine_pro] %d sized_signals chargés depuis %s", len(sized), sized_path)

    # Orders candidates (pass-through)
    orders_candidate: List[Dict[str, Any]] = []
    for it in sized:
        if isinstance(it, dict):
            o = dict(it)
            o.setdefault("source", "derived_from_sized_signals")
            orders_candidate.append(o)

    # Load KING + kill_switch
    king, gov_loaded = _load_king_governance(data_dir)
    ks = _load_kill_switch(data_dir)

    # Derive governance fields (KING is truth)
    gov = {
        "mode": king.get("mode"),
        "soft_veto": bool(king.get("soft_veto", False)),
        "hard_block": bool(king.get("hard_block", False)),
        "action_policy": king.get("action_policy"),
        "reasons": _as_list(king.get("reasons")),
        "kill_switch_reasons": _as_list(ks.get("reasons") or ks.get("reason")),
        "king_source": king.get("_king_source"),
        "source": "execution_engine_pro",
        "env": env,
        "generated_at": now_iso,
    }

    # Hard block (KING / kill_switch / risk_engine guard)
    hard_block, hb_reasons = _derive_hard_block(king, ks, data_dir)
    if hard_block and hb_reasons:
        # ensure reasons reflect the hard block
        gov["hard_block"] = True
        gov["reasons"] = hb_reasons

    # Apply caps on candidate orders (even if soft_veto)
    orders_out, caps_meta = _apply_caps(orders_candidate, data_dir, king)
    gov["caps_meta"] = caps_meta

    # Apply action policy annotation (SIMULATED_ONLY)
    _annotate_action_policy(orders_out, king)

    # Build plan_obj
    plan_obj: Dict[str, Any] = {
        "status": "blocked" if hard_block else ("soft_veto_caution" if gov.get("soft_veto") else "ready"),
        "source": "execution_engine_pro",
        "run_id": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        "env": env,
        "generated_at": now_iso,
        "governance": gov,
        "orders": [] if hard_block else orders_out,
        "reasons": gov.get("reasons") or [],
        "gov_reasons": gov.get("reasons") or [],
        "note": "SAFE_PREPROD_MINIMAL",
    }

    # Always write execution_plan.json (avoid stale)
    save_json_file(execution_plan_path, plan_obj)
    logger.info("[execution_engine_pro] execution_plan.json sauvegardé (%s, orders=%d)", execution_plan_path, len(plan_obj.get("orders", [])))

    # PREPROD simulated plan (keep candidate orders to inspect formatting even if hard_block)
    try:
        if env == "PREPROD" and os.getenv("PREPROD_SIMULATE_ORDERS", "true").lower() == "true":
            sim_payload = {
                "status": "simulated",
                "execution_mode": "SIMULATED_ONLY",
                "env": env,
                "generated_at": now_iso,
                "governance": gov,
                "orders": orders_out,  # capped + annotated
                "reasons": plan_obj.get("reasons") or [],
                "note": "preprod_simulated_plan",
            }
            save_json_file(execution_plan_sim_path, sim_payload)
            logger.info("[execution_engine_pro] execution_plan_simulated.json sauvegardé (%s, orders=%d)", execution_plan_sim_path, len(sim_payload.get("orders", [])))
    except Exception:
        logger.exception("[execution_engine_pro] failed to write execution_plan_simulated.json")

    # Engine state summary
    summary = {
        "timestamp": now_iso,
        "env": env,
        "signals_in": len(sized),
        "orders_candidate": len(orders_candidate),
        "orders_out": 0 if hard_block else len(orders_out),
        "hard_block": bool(hard_block),
        "soft_veto": bool(gov.get("soft_veto")),
        "action_policy": gov.get("action_policy"),
        "reasons": plan_obj.get("reasons") or [],
        "king_source": gov.get("king_source"),
    }
    save_json_file(engine_state_path, summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
