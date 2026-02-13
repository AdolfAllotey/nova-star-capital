#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Minimal required artifacts for this brique
REQ_FILES = [
    Path("data/equities_offensive/execution/execution_plan.json"),
    Path("data/equities_offensive/execution/simulated_fills.jsonl"),
    Path("data/equities_offensive/state/positions.json"),
    Path("data/equities_offensive/state/exposure_snapshot.json"),
    Path("data/equities_offensive/state/limits_report.json"),
    Path("data/equities_offensive/state/position_report.json"),
    Path("data/equities_offensive/ui/ui_bundle.json"),
    Path("data/equities_offensive/ui/audit_trail.jsonl"),
]

# Optional but recommended
OPT_FILES = [
    Path("data/market/market_regime.json"),
    Path("data/ops/us_holidays.json"),
    Path("data/governance/governance_engine_pro.json"),
]

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any=None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl_nonempty(path: Path, max_lines: int = 5) -> Tuple[bool, int]:
    if not path.exists():
        return False, 0
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
            if n >= max_lines:
                break
    return True, n

def check_required_files() -> Tuple[bool, List[str]]:
    ok = True
    reasons = []
    for p in REQ_FILES:
        if not p.exists():
            ok = False
            reasons.append(f"missing: {p}")
    return ok, reasons

def check_execution_plan() -> Tuple[bool, List[str]]:
    ok = True
    reasons = []
    plan = load_json(Path("data/equities_offensive/execution/execution_plan.json"), default={}) or {}
    if not isinstance(plan, dict):
        return False, ["execution_plan.json not a dict"]

    for k in ["plan_id", "action_policy"]:
        if k not in plan:
            ok = False
            reasons.append(f"execution_plan missing key: {k}")

    # Safe default in preprod: SIMULATED_ONLY
    pol = (plan.get("action_policy") or "").upper()
    if pol not in {"SIMULATED_ONLY", "EXIT_ONLY", "LIVE"}:
        ok = False
        reasons.append(f"unknown action_policy={pol}")

    # Orders list shape
    orders = plan.get("orders", [])
    if orders is None:
        orders = []
    if not isinstance(orders, list):
        ok = False
        reasons.append("execution_plan.orders not a list")
    else:
        for i, o in enumerate(orders[:20]):
            if not isinstance(o, dict):
                ok = False
                reasons.append(f"order[{i}] not a dict")
                continue
            if "symbol" not in o or "side" not in o or "qty" not in o:
                ok = False
                reasons.append(f"order[{i}] missing one of (symbol,side,qty)")

    return ok, reasons

def check_limits() -> Tuple[bool, List[str]]:
    lim = load_json(Path("data/equities_offensive/state/limits_report.json"), default={}) or {}
    if not isinstance(lim, dict):
        return False, ["limits_report.json not a dict"]
    # Must contain ok + soft_vetos
    if "ok" not in lim:
        return False, ["limits_report missing ok"]
    if "soft_vetos" not in lim or not isinstance(lim.get("soft_vetos"), list):
        return False, ["limits_report missing soft_vetos list"]
    return True, []

def check_ui_bundle() -> Tuple[bool, List[str]]:
    ui = load_json(Path("data/equities_offensive/ui/ui_bundle.json"), default={}) or {}
    if not isinstance(ui, dict):
        return False, ["ui_bundle.json not a dict"]
    for k in ["kpis", "exposure", "limits", "plan", "recent_fills"]:
        if k not in ui:
            return False, [f"ui_bundle missing {k}"]
    if not isinstance(ui.get("kpis"), dict):
        return False, ["ui_bundle.kpis not dict"]
    return True, []

def check_jsonl_files() -> Tuple[bool, List[str]]:
    ok = True
    reasons = []

    exists, n = read_jsonl_nonempty(Path("data/equities_offensive/execution/simulated_fills.jsonl"))
    if not exists:
        ok = False
        reasons.append("missing simulated_fills.jsonl")
    # can be empty in weekend/simulated_only => OK, just record

    exists2, n2 = read_jsonl_nonempty(Path("data/equities_offensive/ui/audit_trail.jsonl"))
    if not exists2:
        ok = False
        reasons.append("missing audit_trail.jsonl")
    elif n2 == 0:
        ok = False
        reasons.append("audit_trail.jsonl is empty (should have at least 1 event)")

    return ok, reasons

def optional_warnings() -> List[str]:
    warns = []
    for p in OPT_FILES:
        if not p.exists():
            warns.append(f"optional missing: {p}")
    return warns

def main():
    report = {
        "ts": utc_now_iso(),
        "engine": "equ_preprod_check_v1",
        "ok": True,
        "checks": [],
        "warnings": [],
    }

    def run(name, fn):
        nonlocal report
        ok, reasons = fn()
        report["checks"].append({"name": name, "ok": ok, "reasons": reasons})
        if not ok:
            report["ok"] = False

    run("required_files", check_required_files)
    run("execution_plan", check_execution_plan)
    run("limits_report", check_limits)
    run("ui_bundle", check_ui_bundle)
    run("jsonl_files", check_jsonl_files)

    report["warnings"] = optional_warnings()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["ok"] else 2)

if __name__ == "__main__":
    main()
