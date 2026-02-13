#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

OUT_PATH = Path("data/ops/health.json")
THRESH_PATH = Path("data/ops/health_thresholds.json")

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def file_age_sec(path: Path) -> float:
    if not path.exists():
        return 1e18
    return max(0.0, (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime))

def status_rollup(items: List[Dict[str, Any]]) -> str:
    # FAIL > WARN > OK
    s = "OK"
    for it in items:
        if it.get("status") == "FAIL":
            return "FAIL"
        if it.get("status") == "WARN":
            s = "WARN"
    return s

def check_file_fresh(path: str, max_age: int) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"check": "file_fresh", "path": path, "status": "FAIL", "msg": "missing"}
    age = file_age_sec(p)
    if age > max_age:
        return {"check": "file_fresh", "path": path, "status": "WARN", "msg": f"stale age_sec={int(age)}"}
    return {"check": "file_fresh", "path": path, "status": "OK", "msg": f"age_sec={int(age)}"}

def check_trading_window() -> Dict[str, Any]:
    p = Path("data/ops/trading_window.json")
    doc = load_json(p, default=None)
    if not isinstance(doc, dict):
        return {"check": "trading_window", "status": "WARN", "msg": "trading_window.json missing or invalid"}
    allowed = bool(doc.get("allowed", False))
    return {
        "check": "trading_window",
        "status": "OK" if allowed else "WARN",
        "msg": "allowed" if allowed else "blocked",
        "details": {"reasons": doc.get("reasons", []), "local_ts": doc.get("local_ts")}
    }

def check_execution_plan(th: Dict[str, Any]) -> Dict[str, Any]:
    p = Path("data/equities_offensive/execution/execution_plan.json")
    doc = load_json(p, default=None)
    if not isinstance(doc, dict):
        return {"check": "execution_plan", "status": "FAIL", "msg": "missing or invalid"}
    action_policy = doc.get("action_policy")
    orders = doc.get("orders") or []
    cand = doc.get("candidate_orders") or []
    st = "OK"
    msgs = []
    if action_policy == "SIMULATED_ONLY" and th.get("fail_on_orders_in_simulated_only", True):
        if len(orders) != 0:
            st = "FAIL"
            msgs.append("SIMULATED_ONLY but orders!=0")
    if len(cand) == 0:
        st = "WARN" if st != "FAIL" else st
        msgs.append("candidate_orders=0")
    return {
        "check": "execution_plan",
        "status": st,
        "msg": "; ".join(msgs) if msgs else "ok",
        "details": {"plan_id": doc.get("plan_id"), "action_policy": action_policy, "orders": len(orders), "candidate_orders": len(cand)}
    }

def check_signals(th: Dict[str, Any]) -> Dict[str, Any]:
    p = Path("data/equities_offensive/signals/signals_v1.json")
    doc = load_json(p, default=None)
    if not isinstance(doc, dict):
        return {"check": "signals", "status": "WARN", "msg": "signals missing"}
    signals = doc.get("signals") or []
    min_expected = int(th.get("min_signals_expected", 1))
    if len(signals) < min_expected:
        return {"check": "signals", "status": "WARN", "msg": f"signals={len(signals)} < {min_expected}"}
    return {"check": "signals", "status": "OK", "msg": f"signals={len(signals)}"}

def check_positions() -> Dict[str, Any]:
    p = Path("data/equities_offensive/state/exposure_snapshot.json")
    doc = load_json(p, default=None)
    if not isinstance(doc, dict):
        return {"check": "positions", "status": "WARN", "msg": "exposure snapshot missing"}
    return {
        "check": "positions",
        "status": "OK",
        "msg": f"open_positions={doc.get('open_positions',0)} total_notional_usd={doc.get('total_notional_usd',0)}"
    }

def build_health() -> Dict[str, Any]:
    th = load_json(THRESH_PATH, default={}) or {}
    max_age = int(th.get("max_file_age_sec", 7200))

    checks: List[Dict[str, Any]] = []

    # Freshness (key artifacts)
    for fp in [
        "data/ops/trading_window.json",
        "data/market/market_regime.json",
        "data/equities_offensive/execution/execution_plan.json",
        "data/equities_offensive/reporting/dashboard_payload.json",
    ]:
        checks.append(check_file_fresh(fp, max_age))

    checks.append(check_trading_window())
    checks.append(check_signals(th))
    checks.append(check_execution_plan(th))
    checks.append(check_positions())

    status = status_rollup(checks)

    out = {
        "ts": utc_now_iso(),
        "engine": "healthcheck_builder_v1",
        "status": status,
        "checks": checks,
        "thresholds": th,
        "host": {
            "hostname": os.uname().nodename if hasattr(os, "uname") else None,
        }
    }
    save_json(OUT_PATH, out)
    return out

def main():
    out = build_health()
    print(json.dumps({"status": out["status"], "ts": out["ts"]}, ensure_ascii=False, indent=2))
    if out["status"] == "FAIL":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
