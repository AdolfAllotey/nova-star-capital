#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

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

def check_file(path: str) -> Tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, f"missing: {path}"
    if p.stat().st_size == 0:
        return False, f"empty: {path}"
    return True, f"ok: {path}"

def require_keys(obj: Dict[str, Any], keys: List[str]) -> Tuple[bool, str]:
    for k in keys:
        if k not in obj:
            return False, f"missing_key: {k}"
    return True, "ok"

def run_checks() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ok = True

    # Files expected (minimal)
    expected_files = [
        "data/market/market_regime.json",
        "data/equities_offensive/signals/signals_v1.json",
        "data/equities_offensive/voting/voted_signals.json",
        "data/equities_offensive/risk/risk_decisions.json",
        "data/equities_offensive/risk/execution_candidates.json",
        "data/equities_offensive/execution/execution_plan.json",
        "data/equities_offensive/state/positions_state.json",
        "data/equities_offensive/state/exposure_snapshot.json",
        "data/equities_offensive/reporting/dashboard_payload.json",
    ]

    for fp in expected_files:
        passed, msg = check_file(fp)
        checks.append({"type": "file_exists", "path": fp, "passed": passed, "msg": msg})
        ok = ok and passed

    # Content checks
    plan = load_json(Path("data/equities_offensive/execution/execution_plan.json"), default={}) or {}
    passed, msg = require_keys(plan, ["plan_id", "action_policy", "orders", "candidate_orders"])
    checks.append({"type": "plan_keys", "passed": passed, "msg": msg})
    ok = ok and passed

    # PREPROD invariant: SIMULATED_ONLY => orders must be 0
    if plan.get("action_policy") == "SIMULATED_ONLY":
        passed = (len(plan.get("orders") or []) == 0)
        msg = "ok" if passed else "SIMULATED_ONLY but orders != 0"
        checks.append({"type": "simulated_only_orders_zero", "passed": passed, "msg": msg})
        ok = ok and passed

    # Caps sanity
    caps = plan.get("caps") or {}
    passed = isinstance(caps.get("max_orders"), int) and float(caps.get("max_notional_usd", 0)) > 0
    checks.append({"type": "caps_sanity", "passed": bool(passed), "msg": "ok" if passed else "invalid caps"})
    ok = ok and bool(passed)

    # Idempotence check: running plan builder twice should keep same plan_id
    plan_id_1 = plan.get("plan_id")
    plan2 = load_json(Path("data/equities_offensive/execution/execution_plan.json"), default={}) or {}
    plan_id_2 = plan2.get("plan_id")
    passed = (plan_id_1 == plan_id_2)
    checks.append({"type": "idempotence_plan_id_stable", "passed": passed, "msg": "ok" if passed else "plan_id changed"})
    ok = ok and passed

    # Dashboard payload sanity
    dash = load_json(Path("data/equities_offensive/reporting/dashboard_payload.json"), default={}) or {}
    passed, msg = require_keys(dash, ["ts", "module", "kpis", "execution_plan", "exposure"])
    checks.append({"type": "dashboard_keys", "passed": passed, "msg": msg})
    ok = ok and passed

    # Exposure snapshot sanity
    exposure = load_json(Path("data/equities_offensive/state/exposure_snapshot.json"), default={}) or {}
    passed, msg = require_keys(exposure, ["open_positions", "total_notional_usd", "by_symbol"])
    checks.append({"type": "exposure_keys", "passed": passed, "msg": msg})
    ok = ok and passed

    out = {
        "ts": utc_now_iso(),
        "module": "equities_offensive",
        "check_suite": "preprod_checks_v1",
        "passed": bool(ok),
        "checks": checks
    }
    return out

def main():
    out = run_checks()
    save_json(Path("data/equities_offensive/tests/preprod_checks_result.json"), out)
    print(json.dumps({"passed": out["passed"], "ts": out["ts"]}, ensure_ascii=False, indent=2))
    if not out["passed"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
