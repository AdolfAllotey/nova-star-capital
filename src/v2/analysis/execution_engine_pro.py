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

import sys
import os

# NSC_ENFORCE_CLI_DATA_DIR_V1
# Ensure --data-dir actually drives the data directory for this process.
# This guarantees file_utils.get_data_dir() and any env-based resolution uses the CLI value.
try:
    _dd = _resolve_data_dir_override()
    if _dd:
        os.environ["NSC_DATA_DIR"] = str(_dd)
except Exception:
    pass

# ---------------------------------------------------------------------------
# NSC: DATA_DIR override (CLI --data-dir > env NSC_DATA_DIR/NCS_DATA_DIR)
# ---------------------------------------------------------------------------
def _resolve_data_dir_override(argv=None):
    argv = argv or sys.argv
    if '--data-dir' in argv:
        try:
            return argv[argv.index('--data-dir') + 1]
        except Exception:
            return None
    return os.getenv('NSC_DATA_DIR') or os.getenv('NCS_DATA_DIR') or None

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
    # --- NSC_FORCE_SIMULATED_ONLY_IN_PREPROD_V2 ---
    _env = (os.getenv("NSC_ENV", "") or "").upper()
    _dry = str(os.getenv("NSC_DRY_RUN", "") or "").lower() in ("1","true","yes") or _env == "PREPROD"
    if _dry:
        mode = "SIMULATED_ONLY"

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






def _sync_order_notional_fields(plan_obj):
    """
    PREPROD consistency rule:
    after qty/price rounding, force all notional fields to the same effective value.
    """
    try:
        orders = plan_obj.get("orders", [])
        if not isinstance(orders, list):
            return plan_obj

        for o in orders:
            if not isinstance(o, dict):
                continue

            requested = o.get("notional_eur")
            if requested is not None:
                o["requested_notional_eur"] = requested

            qty = o.get("qty")
            px = o.get("price_ref")
            effective = None

            try:
                if qty is not None and px is not None:
                    q = float(qty)
                    pxf = float(px)
                    if q > 0 and pxf > 0:
                        effective = round(q * pxf, 8)
            except Exception:
                effective = None

            if effective is None:
                try:
                    effective = round(float(o.get("notional_eur") or o.get("notional") or 0.0), 8)
                except Exception:
                    effective = None

            if effective is not None and effective > 0:
                o["effective_notional_eur"] = effective
                o["notional_eur"] = effective
                o["notional"] = effective

        return plan_obj
    except Exception:
        return plan_obj

def _nsc_route_exchange_from_pool(symbol: str, idx: int, data_dir: Path) -> str:
    """
    PREPROD broker-pool routing:
    - reads capital/capital_pools.json
    - distributes crypto orders across enabled crypto exchanges
    - deterministic round-robin to avoid sending everything to Binance
    """
    try:
        pools_path = Path(data_dir) / "capital" / "capital_pools.json"
        pools = _read_json(pools_path, default={}) or {}
        brokers = (((pools.get("pools") or {}).get("crypto_exchange_pool") or {}).get("brokers") or {})
        exchanges = [str(k).lower() for k, v in brokers.items() if float(v or 0) > 0]
        exchanges = [e for e in exchanges if e in {"binance", "mexc"}]
        if exchanges:
            return exchanges[int(idx) % len(exchanges)]
    except Exception:
        pass
    return "binance"

def _enrich_orders(orders, data_dir, execution_mode="LIVE"):
    """
    Enrich orders with: notional_eur, execution_mode, exchange, qty (if missing).
    Best-effort only. Never raises.
    """
    try:
        from pathlib import Path
        import json

        # Robust price map loader
        def _extract_price_value(v):
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, dict):
                for kk in ("price", "last", "close", "mid", "value"):
                    vv = v.get(kk)
                    if isinstance(vv, (int, float)):
                        return float(vv)
            return None

        def _merge_price_dict(dst, src):
            if not isinstance(src, dict):
                return dst
            for k, v in src.items():
                px = _extract_price_value(v)
                if px is not None and px > 0:
                    dst[str(k).lower()] = float(px)
            return dst

        pm = {}

        # 1) prices.json
        try:
            prices_path = Path(data_dir) / "market" / "prices.json"
            if prices_path.exists():
                obj = json.loads(prices_path.read_text(encoding="utf-8"))
                if isinstance(obj, dict):
                    pm = _merge_price_dict(pm, obj.get("prices"))
                    pm = _merge_price_dict(pm, obj.get("tickers"))
                    pm = _merge_price_dict(pm, obj)
        except Exception:
            pass

        # 2) Merge crypto spot sources even if pm already exists
        try:
            _cand = [
                Path(data_dir) / "market" / "crypto_spot_prices.json",
                Path(data_dir) / "market" / "crypto_prices.json",
                Path(data_dir) / "market" / "tickers.json",
                Path(data_dir) / "analysis" / "crypto_spot_prices.json",
            ]
            for _pp in _cand:
                try:
                    if _pp.exists():
                        obj = _read_json(_pp, default=None)
                        if isinstance(obj, dict):
                            pm = _merge_price_dict(pm, obj.get("prices"))
                            pm = _merge_price_dict(pm, obj.get("tickers"))
                            pm = _merge_price_dict(pm, obj)
                except Exception:
                    continue
        except Exception:
            pass

        # Exchange router (optional)
        router = None
        try:
            from src.v2.core.exchange_router import get_exchange_for_token as router
        except Exception:
            router = None

        filled = 0
        total = 0

        for o in orders or []:
            if not isinstance(o, dict):
                continue
            total += 1

            # execution_mode
            o["execution_mode"] = execution_mode

            # unify notional
            if "notional_eur" not in o and isinstance(o.get("notional"), (int, float)):
                o["notional_eur"] = float(o["notional"])

            # exchange
            if callable(router) and not o.get("exchange"):
                try:
                    o["exchange"] = router(o.get("symbol"))
                except Exception:
                    pass

            # PREPROD MASTER RULE:
            # Force broker-pool routing even if an upstream fallback already set exchange=binance.
            try:
                if str(os.getenv("NSC_ENV") or "").upper() == "PREPROD" or str(data_dir).endswith("/preprod"):
                    o["exchange"] = _nsc_route_exchange_from_pool(o.get("symbol"), total - 1, Path(data_dir))
            except Exception:
                pass

            # qty compute if missing
            if (o.get("qty") is None or (isinstance(o.get("qty"), (int,float)) and float(o["qty"]) <= 0)) and isinstance(o.get("notional_eur"), (int, float)):
                sym = str(o.get("symbol","")).lower().strip()
                # normalize common forms: "btc/usdt" -> "btc"
                base = sym.split("/")[0].split("-")[0].split("_")[0]
                px = pm.get(base) or pm.get(base.replace("usdt",""))
                if isinstance(px, (int, float)) and px > 0:
                    # NSC_QTY_FROM_NOTIONAL_USDT_V1
                    # Prefer USDT notional if available; fallback to EUR notional.
                    _n = o.get('notional')
                    if not isinstance(_n, (int, float)):
                        _n = o.get('notional_usdt')
                    if not isinstance(_n, (int, float)):
                        _n = o.get('notional_eur')
                    q = float(_n) / float(px)

                    if q > 0:
                        # NSC_QTY_ROUND_USE_FILTERS_V1
                        # NSC_FIX_UNDEFINED_ROUND_TO_V1
                        # NSC_FIX_QTY_ASSIGN_FROM_Q_V1
                        o['qty'] = _round_qty(o.get('symbol',''), q)

                        # NSC_SET_PRICE_REF_AND_CLEAR_SNAPSHOT_ERROR_V1
                        # Keep the price reference we used to compute qty
                        o["price_ref"] = float(px)
                        # If we managed to resolve a price, clear the previous missing snapshot error
                        try:
                            ve = o.get("validation_errors")
                            if isinstance(ve, list) and "missing_price_snapshot" in ve:
                                o["validation_errors"] = [e for e in ve if e != "missing_price_snapshot"]
                                if not o["validation_errors"]:
                                    o.pop("validation_errors", None)
                        except Exception:
                            pass
                        filled += 1

        try:
            logger.info("[execution_engine_pro] enrich_orders: qty_filled=%d/%d mode=%s", filled, total, execution_mode)
        except Exception:
            pass

    except Exception:
        try:
            logger.exception("[execution_engine_pro] enrich_orders failed")
        except Exception:
            pass


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


# ================================
# NSC_EXCHANGE_ROUNDING_V1
# ================================

def _round_qty(symbol: str, qty: float) -> float:
    try:
        q = float(qty)
    except Exception:
        return qty

    s = (symbol or "").lower()

    if s.startswith("bnb"):
        decimals = 6
    else:
        decimals = 8

    m = 10 ** decimals
    return round(q * m) / m


def _apply_rounding_and_min_notional(plan_obj: dict, env_upper: str, data_dir: str | None = None, logger=None):
    orders = plan_obj.get("orders")
    if not isinstance(orders, list):
        return

    # NSC_EXCHANGE_FILTERS_JSON_WIRING_V1
    filters = _load_exchange_filters(data_dir) if data_dir else {}

    for o in orders:

    # NSC_EXCHANGE_FILTERS_JSON_USE_V1

        symbol = (o.get('symbol') or '').lower()

        exchange = (o.get('exchange') or _nsc_route_exchange_from_pool(str(o.get("symbol") or ""), i, data_dir)).lower()
        o["exchange"] = exchange

        f = _get_filters_for_symbol(filters, exchange, symbol)

        try:

            min_notional_eur = float(f.get('min_notional_eur', 5.0))

        except Exception:

            min_notional_eur = 5.0

        try:

            qty_decimals = int(f.get('qty_decimals', 8))

        except Exception:

            qty_decimals = 8
        if not isinstance(o, dict):
            continue

        sym = o.get("symbol")
        qty = o.get("qty")
        notional = o.get("notional")

        if qty is not None:
            o["qty"] = _round_qty(sym, qty)

        min_notional = 5.0

        try:
            n = float(notional)
        except Exception:
            n = 0.0

        o.setdefault("exchange_validation", {})
        o["exchange_validation"]["min_notional_eur"] = min_notional
        o["exchange_validation"]["min_notional_ok"] = (n >= min_notional)
# NSC_PREPROD_MIN_NOTIONAL_FLOOR_V1
        # PREPROD only: if notional is below exchange min-notional, bump it to min_notional
        # so simulated plans remain exchange-realistic and UI/telemetry do not show impossible orders.
        try:
            if str(env_upper).upper() == "PREPROD":
                if isinstance(n, (int, float)) and n > 0 and n < float(min_notional):
                    ratio = float(min_notional) / float(n)
                    # bump notional
                    o["notional"] = float(min_notional)
                    o["notional_eur"] = float(min_notional)

                    # scale qty if present
                    try:
                        q0 = o.get("qty")
                        if isinstance(q0, (int, float)) and float(q0) > 0:
                            o["qty"] = _round_qty(str(o.get("symbol","")), float(q0) * ratio)
                    except Exception:
                        pass

                    o.setdefault("exchange_validation", {})
                    o["exchange_validation"]["min_notional_bumped"] = True
                    o["exchange_validation"]["min_notional_ok"] = True
        except Exception:
            pass






    # NSC_DROP_ORDERS_UNDER_MIN_NOTIONAL_V1
    # NSC_MIN_NOTIONAL_REASON_DEDUP_V1
    def _add_reason_once(lst, msg):
        try:
            if not isinstance(lst, list):
                return
            if msg not in lst:
                lst.append(msg)
        except Exception:
            pass

    # If exchange min-notional is not satisfied, drop orders (caps may conflict with min_notional).
    try:
        orders = plan_obj.get("orders")
        if isinstance(orders, list) and orders:
            kept = []
            dropped = []
            for o in orders:
                ev = o.get("exchange_validation") or {}
                ok = ev.get("min_notional_ok")
                if ok is False and env_upper != "PREPROD":
                    dropped.append(o)
                else:
                    kept.append(o)

            if dropped:
                # governance metadata
                gov = plan_obj.get("governance")
                if isinstance(gov, dict):
                    gov.setdefault("caps_meta", {})
                    gov["caps_meta"]["dropped_min_notional"] = len(dropped)
                    gov["caps_meta"]["kept_before_min_notional"] = len(orders)
                    gov["caps_meta"]["kept_after_min_notional"] = len(kept)
                    gov["caps_meta"]["kept_final"] = len(kept)
# NSC_CAPS_META_KEPT_FINAL_V1
                    # Keep "kept" consistent: reflect FINAL kept after all filters
                    try:
                        gov["caps_meta"]["kept"] = gov["caps_meta"].get("kept_final", len(kept))
                    except Exception:
                        pass
                    gov["caps_meta"]["min_notional_drop"] = True

                # attach a short sample (avoid bloat)
                try:
                    sample = []
                    for o in dropped[:5]:
                        sample.append({
                            "symbol": o.get("symbol"),
                            "notional": o.get("notional"),
                            "min_notional_eur": (o.get("exchange_validation") or {}).get("min_notional_eur"),
                        })
                    if isinstance(gov, dict):
                        gov["caps_meta"]["dropped_min_notional_sample"] = sample
                except Exception:
                    pass

                # apply keep
                plan_obj["orders"] = kept

                # If everything dropped => mark empty/blocked semantics
                if not kept:
                    plan_obj["status"] = "empty"
                    plan_obj["plan_empty_due_to_min_notional"] = True
                    if isinstance(gov, dict):
                        gov["soft_veto"] = True
                        gov.setdefault("reasons", [])
                        _add_reason_once(gov["reasons"], "All orders dropped: exchange min-notional not satisfied (caps conflict).")
                    plan_obj.setdefault("reasons", [])
                    _add_reason_once(plan_obj["reasons"], "All orders dropped: exchange min-notional not satisfied (caps conflict).")

    except Exception:
        if logger:
            logger.exception("[execution_engine_pro] min-notional drop step failed")

# NSC_EXCHANGE_FILTERS_JSON_HELPERS_V1
def _load_exchange_filters(data_dir: str):
    """Load exchange filters from DATA_DIR/config/exchange_filters.json (optional)."""
    try:
        from pathlib import Path
        import json
        cfg = Path(data_dir) / "config" / "exchange_filters.json"
        if not cfg.exists():
            return {}
        return json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_filters_for_symbol(filters: dict, exchange: str, symbol: str):
    exchange = (exchange or "").lower()
    symbol = (symbol or "").lower()
    ex = (filters.get("exchanges") or {}).get(exchange) or {}
    defaults = ex.get("defaults") or {}
    sym = (ex.get("symbols") or {}).get(symbol) or {}
    out = {}
    out.update(defaults)
    out.update(sym)
    return out

def main() -> int:
    # NSC_ENFORCE_CLI_DATA_DIR_V2
    # CLI --data-dir must drive the runtime data dir for this process.
    try:
        _dd = _resolve_data_dir_override()
        if _dd:
            os.environ["NSC_DATA_DIR"] = str(_dd)
    except Exception:
        pass
    # NSC: apply DATA_DIR override early (so all paths use the same data_dir)
    _dd = _resolve_data_dir_override()
    if _dd:
        try:
            # Prefer an existing set_data_dir() if present in this module
            if 'set_data_dir' in globals() and callable(globals()['set_data_dir']):
                globals()['set_data_dir'](_dd)
            else:
                # Fallback: if module has DATA_DIR, overwrite it
                from pathlib import Path as _Path
                globals()['DATA_DIR'] = _Path(str(_dd)).expanduser().resolve()
        except Exception:
            pass

    data_dir = _load_data_dir()
    trading_dir = data_dir / "trading"
    analysis_dir = data_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    env = str(os.getenv("NSC_ENV", "PREPROD")).upper()
    # NSC_ENV_UPPER_DEFINED_V1
    env_upper = str(env).upper()
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

    # NSC QUALITY GATE CONTEXT:
    # sized_signals may not carry momentum_regime, so we enrich from signal_votes.
    signal_votes_path = analysis_dir / "signal_votes.json"
    signal_votes = _read_json(signal_votes_path, default=[]) or []
    vote_by_symbol = {}
    if isinstance(signal_votes, list):
        for v in signal_votes:
            if isinstance(v, dict) and v.get("symbol"):
                vote_by_symbol[str(v.get("symbol")).lower()] = v

    # Orders candidates (pass-through)
    orders_candidate: List[Dict[str, Any]] = []
    for it in sized:
        if isinstance(it, dict):
            o = dict(it)
            meta_score = o.get("meta_score", o.get("momentum_score", 0))
            try:
                meta_score = float(meta_score)
            except Exception:
                meta_score = 0.0

            vote = vote_by_symbol.get(str(o.get("symbol", "")).lower(), {})
            momentum_regime = str(
                o.get("momentum_regime")
                or vote.get("momentum_regime")
                or ""
            ).lower()
            if momentum_regime:
                o["momentum_regime"] = momentum_regime

            # PREPROD: weak / low-score signals must remain inspectable in SIMULATED_ONLY.
            # We annotate them, but we do not drop them from the simulated execution plan.
            if meta_score < 35.0:
                o.setdefault("quality_warnings", [])
                o["quality_warnings"].append(f"quality_warn: meta_score={meta_score:.2f}<35")
                if env_upper != "PREPROD":
                    o.setdefault("validation_errors", [])
                    o["validation_errors"].append(f"quality_block: meta_score={meta_score:.2f}<35")
                    continue

            if momentum_regime == "weak":
                o.setdefault("quality_warnings", [])
                o["quality_warnings"].append("quality_warn: momentum_regime=weak")
                if env_upper != "PREPROD":
                    o.setdefault("validation_errors", [])
                    o["validation_errors"].append("quality_block: momentum_regime=weak")
                    continue

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
        "writer": "execution_engine_pro",
        "env": env,
        "generated_at": now_iso,
        "ts": now_iso,  # NSC_TS_FIELD_V1
        "updated_at": now_iso,  # NSC_UPDATED_AT_FIELD_V1
    }

    # Hard block (KING / kill_switch / risk_engine guard)
    hard_block, hb_reasons = _derive_hard_block(king, ks, data_dir)

    # NSC_PREPROD_FORCE_NO_SOFT_VETO_V1
    try:
        if env_upper == "PREPROD":
            gov["soft_veto"] = False
            gov.pop("soft_veto_reason", None)
            gov.pop("soft_veto_mode", None)
    except Exception:
        pass
    # NSC_PREPROD_SIMULATED_NO_HARDBLOCK_V2 BEGIN
    # In PREPROD, SIMULATED_ONLY is a soft veto (SIMULATED ONLY), never a hard block.
    try:
        _ap = None
        if isinstance(gov, dict):
            _ap = gov.get('action_policy') or gov.get('execution_mode')
        if str(_ap) == 'SIMULATED_ONLY' and str(env).upper() == 'PREPROD':
            if hard_block:
                hard_block = False

            # IMPORTANT NSC:
            # Do NOT convert SIMULATED_ONLY into a soft veto in PREPROD
            # especially when correlation gate is explicitly ignored
            _corr_ignored = bool(gov.get("correlation_gate_state_preprod_ignored", False))

            if not _corr_ignored:
                gov['soft_veto'] = True
                rs = gov.get('reasons') if isinstance(gov.get('reasons'), list) else []
                rs.append('preprod_simulated_only_no_hard_block')
                gov['reasons'] = rs
    except Exception:
        pass
    # NSC_PREPROD_SIMULATED_NO_HARDBLOCK_V2 END
    if hard_block and hb_reasons:
        # ensure reasons reflect the hard block
        gov["hard_block"] = True
        gov["reasons"] = hb_reasons

    # Apply caps on candidate orders (even if soft_veto)
    orders_out, caps_meta = _apply_caps(orders_candidate, data_dir, king)
    gov["caps_meta"] = caps_meta
    try:
        logger.info("[execution_engine_pro][DEBUG] orders_candidate=%d orders_out=%d caps_kept=%s caps_dropped=%s",
                    len(orders_candidate),
                    len(orders_out),
                    (caps_meta or {}).get("kept"),
                    (caps_meta or {}).get("dropped"))
    except Exception:
        pass

    # NSC_PREPROD_SYNC_GOV_SOFT_VETO_V1
    try:
        if env_upper == "PREPROD":
            gov["soft_veto"] = False
            gov.pop("soft_veto_reason", None)
            gov.pop("soft_veto_mode", None)
    except Exception:
        pass

    # Apply action policy annotation (SIMULATED_ONLY)
    _annotate_action_policy(orders_out, king)
    # NSC_ENRICH_MODE_FIX_V1
    if str(env).upper() == 'PREPROD':
        _enrich_orders(orders_out, data_dir, execution_mode='SIMULATED_ONLY')
    else:
        # NSC_PREPROD_ENRICH_ALWAYS_SIMULATED_V2
        # PREPROD must never enrich as LIVE
        if str(env).upper() == 'PREPROD':
            _enrich_orders(orders_out, data_dir, execution_mode='SIMULATED_ONLY')
        else:
            _enrich_orders(orders_out, data_dir, execution_mode='LIVE')

    # NSC_ORDER_VALIDATION_DROP_INVALID_V1
    orders_all_for_sim = list(orders_out or [])
    # PREPROD/DRY_RUN: derive notional + qty from sized_signals.notional_eur using snapshot prices.
    # - notional is expressed in USDT (quote currency)
    # - qty is base asset quantity
    # - invalid orders (missing price/qty) are dropped from main execution_plan.json
    #
    # FX EUR->USDT can be overridden: NSC_FX_EURUSDT (default 1.08)
    fx_eur_usdt = 1.08
    try:
        fx_eur_usdt = float(os.getenv("NSC_FX_EURUSDT", "1.08"))
    except Exception:
        fx_eur_usdt = 1.08

    def _load_snapshot_prices(_data_dir):
        # Prefer crypto spot prices (if present), then analysis/market_snapshot.json (macro)
        cand = [
            Path(_data_dir) / "market" / "crypto_spot_prices.json",
            Path(_data_dir) / "market" / "crypto_prices.json",
            Path(_data_dir) / "market" / "tickers.json",
            Path(_data_dir) / "analysis" / "market_snapshot.json",
            Path(_data_dir) / "market_snapshot.json",
        ]
        for path in cand:
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        snap = json.load(f)
                    return snap or {}
                except Exception:
                    pass
        return {}

    def _get_price_usdt(symbol: str, snap: dict):
        # Try common shapes without assuming exact schema
        sym = (symbol or "").lower()

        aliases = [sym, sym.upper()]
        base = sym
        for suf in ("usdt", "usd", "/usdt", "-usdt", "_usdt"):
            if base.endswith(suf):
                base = base[:-len(suf)]
                break
        aliases.extend([base, base.upper(), f"{base}usdt", f"{base.upper()}USDT"])

        def _pick(d):
            if not isinstance(d, dict):
                return None
            for key in aliases:
                if key in d:
                    return d.get(key)
            return None

        # 1) snap["prices"][symbol_or_base] = float
        prices = snap.get("prices")
        v = _pick(prices)
        try:
            if v is not None:
                return float(v)
        except Exception:
            pass

        # 2) snap["tickers"][symbol_or_base]["last"] or ["price"]
        tickers = snap.get("tickers")
        t = _pick(tickers)
        if isinstance(t, dict):
            for k in ("last", "price", "close", "mid"):
                if k in t:
                    try:
                        return float(t[k])
                    except Exception:
                        pass

        # 3) snap[symbol_or_base] = float or dict with last/price
        for key in aliases:
            if key in snap:
                v = snap.get(key)
                if isinstance(v, (int, float)):
                    return float(v)
                if isinstance(v, dict):
                    for k in ("last", "price", "close", "mid"):
                        if k in v:
                            try:
                                return float(v[k])
                            except Exception:
                                pass

        return None

    snap = _load_snapshot_prices(data_dir)

    # Enrich orders_out with notional (USDT) + qty (base)
    invalid = []
    valid = []
    for o in (orders_out or []):
        sym = o.get("symbol")
        px = _get_price_usdt(sym, snap)

        # NSC_PX_FALLBACK_TO_PRICE_REF_V1
        # If snapshot doesn't provide px but enrich_orders resolved price_ref, use it for validation/qty.
        try:
            _px_ok = (px is not None and float(px) > 0)
        except Exception:
            _px_ok = False
        if not _px_ok:
            pr = o.get('price_ref')
            try:
                prf = float(pr) if pr is not None else None
            except Exception:
                prf = None
            if prf is not None and prf > 0:
                px = prf

        # notional priority: existing notional -> notional_usdt -> notional_eur
        notional = o.get("notional")
        if notional is None:
            nu = o.get("notional_usdt")
            if nu is not None:
                try:
                    notional = float(nu)
                except Exception:
                    notional = None
        if notional is None:
            ne = o.get("notional_eur")
            if ne is not None:
                try:
                    # PREPROD rule: notional_eur is the source of truth.
                    # Do not inflate simulated sizing with EUR->USDT FX conversion.
                    if env_upper == "PREPROD":
                        notional = float(ne)
                    else:
                        notional = float(ne) * fx_eur_usdt
                except Exception:
                    notional = None

        if notional is not None:
            o["notional"] = round(float(notional), 8)

        # qty
        q = o.get("qty")
        qf = None
        try:
            if q is not None:
                qf = float(q)
        except Exception:
            qf = None

        if (qf is None or qf <= 0) and (px is not None) and (notional is not None) and float(px) > 0:
            try:
                qf = float(notional) / float(px)
                o["qty"] = round(qf, 12)
                o["price_ref"] = float(px)
            except Exception:
                qf = None

        # validate
        if (px is None) or (qf is None) or (qf <= 0):
            o.setdefault("validation_errors", [])
            if px is None:
                # NSC_VALIDATION_USES_PRICE_REF_V2
                # If we already resolved a usable price_ref (or px), do not flag snapshot-missing.
                pr = o.get('price_ref')
                try:
                    prf = float(pr) if pr is not None else None
                except Exception:
                    prf = None
                
                px_ok = False
                try:
                    px_ok = (px is not None and float(px) > 0)
                except Exception:
                    px_ok = False
                
                pr_ok = False
                try:
                    pr_ok = (prf is not None and float(prf) > 0)
                except Exception:
                    pr_ok = False
                
                if not (px_ok or pr_ok):
                    o.setdefault('validation_errors', []).append('missing_price_snapshot')
                else:
                    # ensure price_ref is present if px is known
                    if px_ok:
                        try:
                            o['price_ref'] = float(px)
                        except Exception:
                            pass
                    # remove lingering error if any
                    ve = o.get('validation_errors')
                    if isinstance(ve, list) and 'missing_price_snapshot' in ve:
                        o['validation_errors'] = [e for e in ve if e != 'missing_price_snapshot']
                        if not o['validation_errors']:
                            o.pop('validation_errors', None)

            if qf is None or qf <= 0:
                o["validation_errors"].append("missing_or_invalid_qty")
            # NSC_DROP_EMPTY_VALIDATION_ERRORS_V1
            # If validation_errors exists but is empty, treat as valid => remove the key
            try:
                ve = o.get('validation_errors')
                if isinstance(ve, list) and len(ve) == 0:
                    o.pop('validation_errors', None)
            except Exception:
                pass
            invalid.append(o)
        else:
            valid.append(o)

    if invalid:
        rs = gov.get("reasons") if isinstance(gov.get("reasons"), list) else []
        rs.append(f"orders_invalid_dropped={len(invalid)}")
        gov["reasons"] = rs

    orders_out = valid
    gov["writer"] = "execution_engine_pro"

    # NSC_MAIN_PLAN_USES_VALID_ORDERS_V1
    # Use validated orders for main plan; keep full list for simulated inspection
    try:
        orders_all_for_sim = list(orders_out or [])
        orders_out = valid
        gov["invalid_orders_meta"] = {
            "invalid": len(invalid),
            "valid": len(valid),
            "invalid_examples": invalid[:3],
        }
    except Exception:
        pass



    # NSC_PREPROD_PROMOTE_VALID_SIM_ORDERS_TO_MAIN_V1
    # En PREPROD, si les orders_out gardés par les caps sont tous invalides,
    # on promeut les premiers ordres valides enrichis depuis orders_all_for_sim
    # afin que execution_plan.json ne finisse pas vide alors que la simulation est exploitable.
    try:
        if env_upper == "PREPROD":
            _main_orders = orders_out if isinstance(orders_out, list) else []
            _main_valid = []
            for _o in _main_orders:
                if not isinstance(_o, dict):
                    continue
                _errs = _o.get("validation_errors") or []
                if not _errs:
                    _main_valid.append(_o)

            if not _main_valid:
                _sim_orders = orders_all_for_sim if isinstance(locals().get("orders_all_for_sim"), list) else []
                _sim_valid = []
                for _o in _sim_orders:
                    if not isinstance(_o, dict):
                        continue
                    _errs = _o.get("validation_errors") or []
                    if _errs:
                        continue
                    _sim_valid.append(_o)

                try:
                    _caps = ((gov.get("caps_meta") or {}).get("caps") or {}) if isinstance(gov, dict) else {}
                    _max_keep = int(_caps.get("max_orders_per_run") or 0)
                except Exception:
                    _max_keep = 0

                if _max_keep <= 0:
                    _max_keep = len(_sim_valid)

                if _sim_valid:
                    orders_out = _sim_valid[:_max_keep]
                    logger.info(
                        "[execution_engine_pro][PREPROD] promoted valid simulated orders into main plan: kept=%d",
                        len(orders_out),
                    )
            else:
                orders_out = _main_valid
    except Exception:
        logger.exception("[execution_engine_pro][PREPROD] failed to promote valid simulated orders into main plan")

    # Build plan_obj
    logger.info("[execution_engine_pro][DEBUG] build plan_obj hard_block=%s env=%s orders_out=%d", hard_block, env_upper, len(orders_out) if isinstance(orders_out, list) else 0)

    plan_obj: Dict[str, Any] = {
    "status": "blocked" if hard_block else ("ready" if env_upper == "PREPROD" else ("soft_veto_caution" if gov.get("soft_veto") else "ready")),
    "source": "execution_engine_pro",
    "writer": "execution_engine_pro",
    "run_id": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
    "env": env,
    "generated_at": now_iso,
    "governance": gov,
    "orders": [] if hard_block else orders_out,
    "reasons": gov.get("reasons") or [],
    "gov_reasons": gov.get("reasons") or [],
    "note": "SAFE_PREPROD_MINIMAL",
    }

    # --- NSC_TS_FIELD_FORCE_V1 ---
    # Force timestamps even if dict literal had duplicate keys
    try:
        plan_obj['ts'] = now_iso
        plan_obj['updated_at'] = now_iso
    except Exception:
        pass

    # Ensure governance metadata is consistent with plan (writer + run_id)
    try:
        _rid = plan_obj.get('run_id')
        if isinstance(gov, dict):
            gov['writer'] = 'execution_engine_pro'
            gov['run_id'] = _rid
    except Exception:
        pass

    # Always write execution_plan.json (avoid stale)
    # NSC_ENFORCE_RUN_NOTIONAL_CAP_INLINE_V1
    # Enforce max_notional_eur_per_run by scaling orders in plan_obj (qty+notional).
    try:
        _orders = plan_obj.get("orders", [])
        _gov = plan_obj.get("governance") if isinstance(plan_obj.get("governance"), dict) else {}
        _caps = ( _gov.get("caps_meta") or {} ).get("caps") if isinstance((_gov.get("caps_meta") or {}), dict) else None
        _cap = None
        try:
            if isinstance(_caps, dict) and _caps.get("max_notional_eur_per_run") is not None:
                _cap = float(_caps.get("max_notional_eur_per_run"))
        except Exception:
            _cap = None
    
        if isinstance(_orders, list) and _orders and _cap and _cap > 0:
            def _f(x, d=0.0):
                try:
                    return float(x)
                except Exception:
                    return float(d)
    
            _eff_before = sum(_f(o.get("notional"), 0.0) for o in _orders if isinstance(o, dict))
            if _eff_before > _cap + 1e-9:
                _scale = _cap / _eff_before if _eff_before > 0 else 1.0
                for o in _orders:
                    if not isinstance(o, dict):
                        continue
                    if o.get("notional") is not None:
                        o["notional"] = _f(o.get("notional")) * _scale
                    if o.get("qty") is not None:
                        o["qty"] = _f(o.get("qty")) * _scale
    
                # Final cent-level correction: ensure sum(notional) <= cap (handle float rounding)
                _eff_after = sum(_f(o.get("notional"), 0.0) for o in _orders if isinstance(o, dict))
                _delta = _eff_after - _cap
                if _delta > 1e-9:
                    # adjust last order down by delta
                    for o in reversed(_orders):
                        if not isinstance(o, dict):
                            continue
                        n = _f(o.get("notional"), 0.0)
                        if n > 0:
                            o["notional"] = max(0.0, n - _delta)
                            # if price_ref present, recompute qty to match notional better
                            pr = _f(o.get("price_ref"), 0.0)
                            if pr > 0:
                                o["qty"] = _f(o.get("notional")) / pr
                            break
    
                # annotate governance caps_meta
                try:
                    _gov.setdefault("caps_meta", {})
                    if isinstance(_gov.get("caps_meta"), dict):
                        _gov["caps_meta"]["caps_enforced"] = True
                        _gov["caps_meta"]["scale_run"] = _scale
                        _gov["caps_meta"]["eff_total_before"] = _eff_before
                        _gov["caps_meta"]["eff_total_after"] = sum(_f(o.get("notional"), 0.0) for o in _orders if isinstance(o, dict))
                except Exception:
                    pass
                plan_obj["governance"] = _gov
    except Exception:
        pass
    # NSC_ROUNDING_CALLSITE_V1
    # Apply exchange-safe rounding + min-notional AFTER caps/enrich, BEFORE write
    try:
        logger.info('[execution_engine_pro][DEBUG] BEFORE rounding main orders=%d', len(plan_obj.get("orders", []) if isinstance(plan_obj.get("orders", []), list) else []))
        _apply_rounding_and_min_notional(plan_obj, env_upper, data_dir, logger=logger)
        _sync_order_notional_fields(plan_obj)
        logger.info('[execution_engine_pro][DEBUG] AFTER rounding main orders=%d', len(plan_obj.get("orders", []) if isinstance(plan_obj.get("orders", []), list) else []))
    except Exception:
        logger.exception('[execution_engine_pro] rounding/min-notional step failed')
    # NSC_PREPROD_MAIN_PLAN_FALLBACK_FROM_SIM_V2
    # En PREPROD, si le main plan est vide, on le backfill depuis les ordres simulés enrichis.
    try:
        if env_upper == "PREPROD":
            _main_orders = plan_obj.get("orders", [])
            _sim_source_orders = (orders_all_for_sim if 'orders_all_for_sim' in locals() else orders_out)

            if isinstance(_main_orders, list) and len(_main_orders) == 0 and isinstance(_sim_source_orders, list) and len(_sim_source_orders) > 0:
                _fallback_orders = []
                for _o in _sim_source_orders:
                    if isinstance(_o, dict):
                        _x = dict(_o)
                        _x["execution_mode"] = "SIMULATED_ONLY"
                        _x["action"] = "SIMULATED_ONLY"
                        _fallback_orders.append(_x)

                if _fallback_orders:
                    try:
                        _enrich_orders(_fallback_orders, data_dir, execution_mode="SIMULATED_ONLY")
                    except Exception:
                        logger.exception("[execution_engine_pro][PREPROD] enrich fallback main orders failed")

                    plan_obj["orders"] = _fallback_orders
                    plan_obj["status"] = "ready"
                    plan_obj["note"] = "PREPROD_MAIN_FALLBACK_FROM_SIM"
                    logger.info(
                        "[execution_engine_pro][PREPROD] main plan backfilled from simulated source (orders=%d)",
                        len(_fallback_orders),
                    )
    except Exception:
        logger.exception("[execution_engine_pro][PREPROD] fallback main plan from simulated failed")

    save_json_file(execution_plan_path, plan_obj)


    logger.info("[execution_engine_pro] execution_plan.json sauvegardé (%s, orders=%d)", execution_plan_path, len(plan_obj.get("orders", [])))

    # PREPROD simulated plan (keep candidate orders to inspect formatting even if hard_block)
    try:
        if env_upper == 'PREPROD' and os.getenv('PREPROD_SIMULATE_ORDERS', 'true').lower() == 'true':
            _sim_orders = []
            try:
                if 'orders_all_for_sim' in locals() and isinstance(orders_all_for_sim, list) and orders_all_for_sim:
                    _sim_orders = orders_all_for_sim
                elif isinstance(orders_out, list) and orders_out:
                    _sim_orders = orders_out
                elif isinstance(orders_candidate, list) and orders_candidate:
                    _sim_orders = orders_candidate
            except Exception:
                _sim_orders = []

            sim_payload = {
                'status': 'simulated',
                'writer': 'execution_engine_pro',
                'execution_mode': 'SIMULATED_ONLY',
                'env': env,
                'generated_at': now_iso,
                'governance': gov,
                'orders': _sim_orders,

                'reasons': plan_obj.get('reasons') or [],
                'note': 'preprod_simulated_plan',
            }
            _enrich_orders(sim_payload.get('orders', []), data_dir, execution_mode='SIMULATED_ONLY')
            # NSC_ROUNDING_CALLSITE_SIM_V1
            # Apply exchange-safe rounding + min-notional BEFORE write (simulated payload)
            try:
                logger.info('[execution_engine_pro][DEBUG] BEFORE rounding sim orders=%d', len(sim_payload.get("orders", []) if isinstance(sim_payload.get("orders", []), list) else []))
                _apply_rounding_and_min_notional(sim_payload, env_upper, data_dir, logger=logger)
                _sync_order_notional_fields(sim_payload)
                logger.info('[execution_engine_pro][DEBUG] AFTER rounding sim orders=%d', len(sim_payload.get("orders", []) if isinstance(sim_payload.get("orders", []), list) else []))
            except Exception:
                logger.exception('[execution_engine_pro] rounding/min-notional step failed (sim_payload)')
            save_json_file(execution_plan_sim_path, sim_payload)
            logger.info('[execution_engine_pro] execution_plan_simulated.json sauvegardé (%s, orders=%d)', execution_plan_sim_path, len(sim_payload.get('orders', [])))

            # NSC_PREPROD_MAIN_PLAN_FALLBACK_AFTER_SIM_VALID_ONLY_V2
            try:
                _main_orders_now = plan_obj.get("orders", [])
                _sim_orders_now = sim_payload.get("orders", [])
                if env_upper == "PREPROD" and isinstance(_main_orders_now, list) and len(_main_orders_now) == 0 and isinstance(_sim_orders_now, list) and len(_sim_orders_now) > 0:
                    _main_fallback = []
                    _main_rejected = []

                    def _is_valid_exec_order(_o):
                        if not isinstance(_o, dict):
                            return False
                        _ve = _o.get("validation_errors")
                        if isinstance(_ve, list) and len(_ve) > 0:
                            return False
                        try:
                            _qty = float(_o.get("qty")) if _o.get("qty") is not None else 0.0
                        except Exception:
                            _qty = 0.0
                        try:
                            _pr = float(_o.get("price_ref")) if _o.get("price_ref") is not None else 0.0
                        except Exception:
                            _pr = 0.0
                        try:
                            _ne = float(_o.get("notional_eur")) if _o.get("notional_eur") is not None else 0.0
                        except Exception:
                            _ne = 0.0
                        return (_qty > 0.0) or (_pr > 0.0 and _ne > 0.0)

                    for _o in _sim_orders_now:
                        if not isinstance(_o, dict):
                            continue
                        _x = dict(_o)
                        _x["execution_mode"] = "SIMULATED_ONLY"
                        _x["action"] = "SIMULATED_ONLY"
                        if _is_valid_exec_order(_x):
                            _main_fallback.append(_x)
                        else:
                            _main_rejected.append(_x)

                    if _main_fallback:
                        try:
                            _enrich_orders(_main_fallback, data_dir, execution_mode='SIMULATED_ONLY')
                        except Exception:
                            logger.exception("[execution_engine_pro][PREPROD] enrich valid fallback failed")

                        try:
                            _tmp_payload = {
                                "writer": "execution_engine_pro",
                                "execution_mode": "SIMULATED_ONLY",
                                "env": env,
                                "generated_at": now_iso,
                                "governance": gov,
                                "orders": _main_fallback,
                                "reasons": plan_obj.get("reasons") or [],
                                "note": "PREPROD_MAIN_FALLBACK_AFTER_SIM_VALID_ONLY_V2",
                            }
                            logger.info("[execution_engine_pro][PREPROD][DEBUG] BEFORE rounding post-fallback main orders=%d", len(_tmp_payload.get("orders", [])))
                            _apply_rounding_and_min_notional(_tmp_payload, env_upper, data_dir, logger=logger)
                            logger.info("[execution_engine_pro][PREPROD][DEBUG] AFTER rounding post-fallback main orders=%d", len(_tmp_payload.get("orders", [])))
                            _main_fallback = _tmp_payload.get("orders", []) if isinstance(_tmp_payload.get("orders", []), list) else []
                        except Exception:
                            logger.exception("[execution_engine_pro][PREPROD] rounding valid fallback failed")

                    plan_obj["orders"] = _main_fallback
                    plan_obj["status"] = "ready" if _main_fallback else "blocked"
                    plan_obj["note"] = "PREPROD_MAIN_FALLBACK_AFTER_SIM_VALID_ONLY_V2"
                    plan_obj["rejected_orders"] = _main_rejected
                    plan_obj["rejected_orders_count"] = len(_main_rejected)

                    save_json_file(execution_plan_path, plan_obj)
                    logger.info(
                        "[execution_engine_pro][PREPROD] main plan backfilled after sim build valid_only kept=%d rejected=%d",
                        len(_main_fallback), len(_main_rejected)
                    )
            except Exception:
                logger.exception("[execution_engine_pro][PREPROD] post-sim main fallback failed")

    except Exception:
        logger.exception('[execution_engine_pro] failed to write execution_plan_simulated.json')
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
