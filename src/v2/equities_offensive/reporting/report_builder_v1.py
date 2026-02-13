#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def summarize_top(items: List[Dict[str, Any]], k: int = 5) -> List[Dict[str, Any]]:
    out = []
    for x in items[:k]:
        out.append({
            "symbol": x.get("symbol"),
            "direction": x.get("direction"),
            "setup": x.get("setup"),
            "meta_score": x.get("meta_score"),
            "engine": x.get("engine"),
        })
    return out

def build_dashboard_payload(
    market_regime_path: str = "data/market/market_regime.json",
    signals_path: str = "data/equities_offensive/signals/signals_v1.json",
    voted_path: str = "data/equities_offensive/voting/voted_signals.json",
    risk_path: str = "data/equities_offensive/risk/risk_decisions.json",
    plan_path: str = "data/equities_offensive/execution/execution_plan.json",
    exposure_path: str = "data/equities_offensive/state/exposure_snapshot.json",
    out_payload: str = "data/equities_offensive/reporting/dashboard_payload.json",
    out_audit: str = "data/equities_offensive/reporting/audit_trail.jsonl",
) -> Dict[str, Any]:

    market = load_json(Path(market_regime_path), default={}) or {}
    signals_doc = load_json(Path(signals_path), default={}) or {}
    voted_doc = load_json(Path(voted_path), default={}) or {}
    risk_doc = load_json(Path(risk_path), default={}) or {}
    plan = load_json(Path(plan_path), default={}) or {}
    exposure = load_json(Path(exposure_path), default={}) or {}

    signals = signals_doc.get("signals") or []
    voted = voted_doc.get("voted") or []
    decisions = (risk_doc.get("decisions") or []) if isinstance(risk_doc, dict) else []
    orders = plan.get("orders") or []

    # key KPIs
    kpis = {
        "market_regime": market.get("regime"),
        "market_confidence": market.get("confidence"),
        "signals_count": len(signals),
        "voted_count": len(voted),
        "risk_decisions_count": len(decisions),
        "execution_candidate_orders": len(plan.get("candidate_orders") or []),
        "execution_orders_final": len(orders),
        "open_positions": exposure.get("open_positions", 0),
        "total_notional_usd": exposure.get("total_notional_usd", 0.0),
        "action_policy": plan.get("action_policy"),
        "plan_id": plan.get("plan_id"),
    }

    payload = {
        "ts": utc_now_iso(),
        "module": "equities_offensive",
        "version": "report_builder_v1",
        "kpis": kpis,
        "market_regime": market,
        "top_voted": summarize_top(voted, k=5),
        "risk_decisions": decisions[:10],   # UI can paginate later
        "execution_plan": {
            "plan_id": plan.get("plan_id"),
            "mode": plan.get("mode"),
            "action_policy": plan.get("action_policy"),
            "caps": plan.get("caps"),
            "notes": plan.get("notes", []),
            "orders": orders
        },
        "exposure": exposure
    }

    save_json(Path(out_payload), payload)

    # audit event (jsonl)
    audit_event = {
        "ts": payload["ts"],
        "event_type": "equities_offensive_dashboard_payload_built",
        "kpis": kpis,
        "plan_id": plan.get("plan_id"),
        "orders_final": len(orders),
    }
    append_jsonl(Path(out_audit), audit_event)

    return payload

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Equities Offensive Report Builder V1")
    ap.add_argument("--out", default="data/equities_offensive/reporting/dashboard_payload.json")
    ap.add_argument("--audit", default="data/equities_offensive/reporting/audit_trail.jsonl")
    args = ap.parse_args()

    payload = build_dashboard_payload(out_payload=args.out, out_audit=args.audit)
    print(json.dumps(payload["kpis"], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
