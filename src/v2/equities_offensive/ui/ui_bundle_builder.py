#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Inputs (read-only)
PLAN_PATH      = Path("data/equities_offensive/execution/execution_plan.json")
FILLS_PATH     = Path("data/equities_offensive/execution/simulated_fills.jsonl")
EXPOSURE_PATH  = Path("data/equities_offensive/state/exposure_snapshot.json")
LIMITS_PATH    = Path("data/equities_offensive/state/limits_report.json")
POSREP_PATH    = Path("data/equities_offensive/state/position_report.json")
REGIME_PATH    = Path("data/market/market_regime.json")  # produced by your market_regime_detector
GOV_PATH       = Path("data/governance/governance_engine_pro.json")  # may be missing

# Outputs
UI_BUNDLE_PATH = Path("data/equities_offensive/ui/ui_bundle.json")
AUDIT_PATH     = Path("data/equities_offensive/ui/audit_trail.jsonl")

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

def main():
    plan     = load_json(PLAN_PATH, default={}) or {}
    exposure = load_json(EXPOSURE_PATH, default={}) or {}
    limits   = load_json(LIMITS_PATH, default={}) or {}
    posrep   = load_json(POSREP_PATH, default={}) or {}
    regime   = load_json(REGIME_PATH, default={}) or {}
    gov      = load_json(GOV_PATH, default={}) or {}

    fills = read_jsonl(FILLS_PATH, limit=50)

    # UI KPIs (stable keys)
    kpis = {
        "regime": pick(regime, ["regime"], default="unknown"),
        "regime_confidence": float(pick(regime, ["confidence"], default=0.0) or 0.0),
        "action_policy": (pick(plan, ["action_policy"], default="SIMULATED_ONLY") or "SIMULATED_ONLY"),
        "plan_id": pick(plan, ["plan_id"], default=None),
        "orders_count": len(plan.get("orders") or []) if isinstance(plan, dict) else 0,
        "candidates_count": len(plan.get("candidate_orders") or []) if isinstance(plan, dict) else 0,
        "open_positions": int(pick(exposure, ["open_positions"], default=0) or 0),
        "total_notional_usd": float(pick(exposure, ["total_notional_usd"], default=0.0) or 0.0),
        "limits_ok": bool(pick(limits, ["ok"], default=True)),
        "soft_vetos": (pick(limits, ["soft_vetos"], default=[]) or []),
    }

    bundle = {
        "ts": utc_now_iso(),
        "engine": "ui_bundle_builder_v1",
        "kpis": kpis,
        "exposure": exposure if isinstance(exposure, dict) else {},
        "limits": limits if isinstance(limits, dict) else {},
        "plan": {
            "plan_id": plan.get("plan_id"),
            "action_policy": plan.get("action_policy"),
            "reasons": plan.get("reasons"),
            "orders": plan.get("orders"),
            "candidate_orders": plan.get("candidate_orders"),
        } if isinstance(plan, dict) else {},
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
    }
    append_jsonl(AUDIT_PATH, audit_evt)

    print(json.dumps({"ui_bundle": str(UI_BUNDLE_PATH), "audit": str(AUDIT_PATH), "kpis": kpis}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
