#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

def data_root() -> Path:
    import os
    return Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

ROOT = data_root()

# Inputs (read-only)
PLAN_PATH      = ROOT / "equities_offensive/execution/execution_plan.json"
FILLS_PATH     = ROOT / "equities_offensive/execution/simulated_fills.jsonl"
EXPOSURE_PATH  = ROOT / "equities_offensive/state/exposure_snapshot.json"
LIMITS_PATH    = ROOT / "equities_offensive/state/limits_report.json"
POSREP_PATH    = ROOT / "equities_offensive/state/position_report.json"
REGIME_PATH    = ROOT / "equities_offensive/market/market_regime.json"
VOTED_PATH     = ROOT / "equities_offensive/voting/voted_signals.json"
SIGNALS_PATH   = ROOT / "equities_offensive/signals/signals_v1.json"

def load_regime() -> dict:
    """
    Read per-brick regime file only (no global fallback).
    """
    import json

    try:
        if not REGIME_PATH.exists():
            return {}
        reg = json.loads(REGIME_PATH.read_text(encoding="utf-8"))
        return reg if isinstance(reg, dict) else {}
    except Exception:
        return {}

GOV_PATH       = ROOT / "equities_offensive/governance/governance_engine_pro.json"  # may be missing

# Outputs
UI_BUNDLE_PATH = ROOT / "equities_offensive/ui/ui_bundle.json"
AUDIT_PATH     = ROOT / "equities_offensive/ui/audit_trail.jsonl"

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

def read_jsonl(path: Path, limit: int = 200) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
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

def pick(d: Any, keys: List[str], default=None):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d:
            return d.get(k)
    return default

def build_protection_snapshot(exposure: Dict[str, Any]) -> Dict[str, Any]:
    positions = exposure.get("positions", []) if isinstance(exposure, dict) else []
    if not isinstance(positions, list):
        positions = []

    protected_positions = []
    protected_count = 0
    trailing_hit_count = 0

    for p in positions:
        if not isinstance(p, dict):
            continue

        symbol = p.get("symbol")
        price = p.get("price")
        stop = p.get("trailing_stop_price")
        pnl_pct = p.get("pnl_pct")
        trailing_pct = p.get("trailing_pct")
        regime = p.get("regime")

        status = "UNPROTECTED"
        try:
            if price is not None and stop is not None:
                price_f = float(price)
                stop_f = float(stop)
                if stop_f > 0:
                    if price_f <= stop_f:
                        status = "TRAILING_HIT"
                        trailing_hit_count += 1
                    else:
                        status = "PROTECTED"
                        protected_count += 1
        except Exception:
            status = "UNPROTECTED"

        protected_positions.append({
            "symbol": symbol,
            "price": price,
            "pnl_pct": pnl_pct,
            "regime": regime,
            "trailing_pct": trailing_pct,
            "trailing_stop_price": stop,
            "protection_status": status,
        })

    return {
        "positions_count": len(protected_positions),
        "protected_count": protected_count,
        "trailing_hit_count": trailing_hit_count,
        "protected_positions": protected_positions,
    }

def main():

    plan     = load_json(PLAN_PATH, default={}) or {}
    exposure = load_json(EXPOSURE_PATH, default={}) or {}
    limits   = load_json(LIMITS_PATH, default={}) or {}
    posrep   = load_json(POSREP_PATH, default={}) or {}
    regime   = load_regime()
    gov      = load_json(GOV_PATH, default={}) or {}
    voted_doc = load_json(VOTED_PATH, default={}) or {}
    signals_doc = load_json(SIGNALS_PATH, default={}) or {}

    voted = voted_doc.get("voted") if isinstance(voted_doc, dict) else []
    signals = signals_doc.get("signals") if isinstance(signals_doc, dict) else []

    if not isinstance(voted, list):
        voted = []
    if not isinstance(signals, list):
        signals = []

    fills = read_jsonl(FILLS_PATH, limit=50)
    protection = build_protection_snapshot(exposure if isinstance(exposure, dict) else {})

    # UI KPIs (stable keys)
    kpis = {
        "regime": pick(regime, ["regime"], default="unknown"),
        "regime_confidence": float(pick(regime, ["confidence"], default=0.0) or 0.0),
        "action_policy": (pick(plan, ["action_policy"], default="SIMULATED_ONLY") or "SIMULATED_ONLY"),
        "plan_id": pick(plan, ["plan_id"], default=None),
        "orders_count": len(plan.get("orders") or []) if isinstance(plan, dict) else 0,
        "candidates_count": len(voted) if voted else (len(plan.get("candidate_orders") or []) if isinstance(plan, dict) else 0),
        "open_positions": int(pick(exposure, ["open_positions"], default=0) or 0),
        "total_notional_usd": float(pick(exposure, ["total_notional_usd"], default=0.0) or 0.0),
        "limits_ok": bool(pick(limits, ["ok"], default=True)),
        "soft_vetos": (pick(limits, ["soft_vetos"], default=[]) or []),
        "protected_positions_count": int(protection.get("protected_count", 0) or 0),
        "trailing_hit_count": int(protection.get("trailing_hit_count", 0) or 0),
    }

    bundle = {
        "ts": utc_now_iso(),
        "engine": "ui_bundle_builder_v1",
        "kpis": kpis,
        "exposure": exposure if isinstance(exposure, dict) else {},
        "limits": limits if isinstance(limits, dict) else {},
        "protection": protection,
        "plan": {
            "plan_id": plan.get("plan_id"),
            "action_policy": plan.get("action_policy"),
            "reasons": plan.get("reasons"),
            "orders": plan.get("orders"),
            "candidate_orders": plan.get("candidate_orders"),
        } if isinstance(plan, dict) else {},
        "signals": signals,
        "voted_signals": voted,
        "top_voted": voted[:5],
        "recent_fills": fills,
        "notes": {
            "governance_mode": pick(gov, ["mode", "state"], default=None),
            "ui_contract": "Stable keys: kpis, exposure, limits, plan, recent_fills",
        }
    }

    save_json(UI_BUNDLE_PATH, bundle)

    # Audit trail (append one event per run)
    audit_evt = {
        "ts": bundle["ts"],
        "type": "UI_BUNDLE",
        "plan_id": kpis["plan_id"],
        "action_policy": kpis["action_policy"],
        "regime": kpis["regime"],
        "open_positions": kpis["open_positions"],
        "total_notional_usd": kpis["total_notional_usd"],
        "limits_ok": kpis["limits_ok"],
        "soft_vetos": kpis["soft_vetos"],
        "protected_positions_count": kpis["protected_positions_count"],
        "trailing_hit_count": kpis["trailing_hit_count"],
    }
    append_jsonl(AUDIT_PATH, audit_evt)

    print(json.dumps({"ui_bundle": str(UI_BUNDLE_PATH), "audit": str(AUDIT_PATH), "kpis": kpis}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
