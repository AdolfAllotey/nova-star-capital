from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA = Path("/opt/nsc/data/preprod")
OUT = DATA / "portfolio" / "audit" / "global_orchestration_audit.json"

ORCH_STATUS = DATA / "portfolio" / "audit" / "orchestration_status.json"
ORCH_CONSISTENCY = DATA / "portfolio" / "audit" / "orchestration_consistency.json"
MASTER_AUDIT = DATA / "portfolio" / "audit" / "master_coherence_audit.json"
FUNDING_PLAN = DATA / "portfolio" / "rebalance" / "funding_plan.json"
EXECUTION_PLAN = DATA / "trading" / "execution_plan.json"
EXECUTION_PLAN_SIM = DATA / "trading" / "execution_plan_simulated.json"
OPEN_POSITIONS = DATA / "trading" / "open_positions.json"
GOVERNANCE = DATA / "analysis" / "governance_engine_pro.json"
RISK_LIMITS = DATA / "trading" / "risk_limits.json"
WORST_TRADES_SUMMARY = DATA / "risk" / "worst_trades_summary.json"
UI_DIST = Path("/opt/nsc/app/src/v2/interface/react/dist")
CONTROL_ROOM_SRC = Path("/opt/nsc/app/src/v2/interface/react/src/pages/ControlRoom.jsx")
LONG_RUN_DAILY_CHECK = DATA / "portfolio" / "audit" / "global_preprod_long_run_daily_check.json"


def load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default



def http_ok(path: str) -> dict[str, Any]:
    url = f"http://127.0.0.1:8000{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return {"ok": 200 <= r.status < 300, "status_code": r.status}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def add_check(checks, domain, name, status, blocking=False, details=None):
    checks.append({
        "domain": domain,
        "name": name,
        "status": status,
        "blocking": bool(blocking),
        "details": details or {},
    })


def main() -> int:
    checks = []

    orch = load(ORCH_STATUS, {})
    consistency = load(ORCH_CONSISTENCY, {})
    master = load(MASTER_AUDIT, {})
    funding = load(FUNDING_PLAN, {})
    execution_plan = load(EXECUTION_PLAN, {})
    execution_plan_sim = load(EXECUTION_PLAN_SIM, {})
    open_positions = load(OPEN_POSITIONS, [])

    active_open_positions = []
    if isinstance(open_positions, list):
        for pos in open_positions:
            if not isinstance(pos, dict):
                continue
            remaining = pos.get("remaining_size", pos.get("size", 0))
            try:
                remaining = float(remaining or 0)
            except Exception:
                remaining = 0.0

            if pos.get("closed") is True or remaining <= 0:
                continue

            active_open_positions.append(pos)
    governance = load(GOVERNANCE, {})
    risk_limits = load(RISK_LIMITS, {})
    worst_trades_summary = load(WORST_TRADES_SUMMARY, {})
    long_run_daily_check = load(LONG_RUN_DAILY_CHECK, {})

    add_check(
        checks,
        "orchestration",
        "orchestration_status_artifact",
        "OK" if orch.get("orchestration_status") == "OK" else "BLOCKING",
        blocking=orch.get("orchestration_status") != "OK",
        details={"orchestration_status": orch.get("orchestration_status")}
    )

    add_check(
        checks,
        "orchestration",
        "orchestration_consistency",
        "OK" if consistency.get("status") == "ok" and not consistency.get("blocking") else "BLOCKING",
        blocking=consistency.get("status") != "ok" or bool(consistency.get("blocking")),
        details={
            "status": consistency.get("status"),
            "blocking": consistency.get("blocking"),
            "alert_level": consistency.get("alert_level"),
            "reasons": consistency.get("reasons"),
        }
    )

    master_summary = master.get("summary", {}) if isinstance(master, dict) else {}
    master_blocking = (
        int(master_summary.get("errors_count", 0) or 0) > 0
        or len(master_summary.get("missing_artifacts", []) or []) > 0
    )

    add_check(
        checks,
        "orchestration",
        "master_coherence_audit",
        "OK" if not master_blocking else "BLOCKING",
        blocking=master_blocking,
        details={
            "status": master.get("status"),
            "errors": master_summary.get("errors_count"),
            "warnings": master_summary.get("warnings_count"),
            "missing": master_summary.get("missing_artifacts"),
        }
    )

    funding_status_ok = funding.get("status") == "ok"
    auto_transfer_allowed = bool(funding.get("auto_transfer_allowed", False))
    manual_approval_required = bool(funding.get("manual_approval_required", False))

    add_check(
        checks,
        "funding",
        "funding_plan_status",
        "OK" if funding_status_ok else "BLOCKING",
        blocking=not funding_status_ok,
        details={"status": funding.get("status")}
    )

    add_check(
        checks,
        "funding",
        "auto_transfer_disabled",
        "OK" if not auto_transfer_allowed else "BLOCKING",
        blocking=auto_transfer_allowed,
        details={"auto_transfer_allowed": auto_transfer_allowed}
    )

    add_check(
        checks,
        "funding",
        "manual_approval_required",
        "OK" if manual_approval_required else "WARNING",
        blocking=False,
        details={"manual_approval_required": manual_approval_required}
    )

    execution_status = execution_plan.get("status") if isinstance(execution_plan, dict) else None
    execution_orders = execution_plan.get("orders", []) if isinstance(execution_plan, dict) else []
    simulated_orders = execution_plan_sim.get("orders", []) if isinstance(execution_plan_sim, dict) else []

    open_positions_count = len(active_open_positions)
    execution_orders_count = len(execution_orders) if isinstance(execution_orders, list) else 0
    simulated_orders_count = len(simulated_orders) if isinstance(simulated_orders, list) else 0

    add_check(
        checks,
        "execution",
        "execution_plan_status",
        "OK" if execution_status in ("ready", "ok", "simulated") else "WARNING",
        blocking=False,
        details={"status": execution_status}
    )

    add_check(
        checks,
        "execution",
        "execution_orders_present",
        "OK" if execution_orders_count >= 0 else "BLOCKING",
        blocking=False,
        details={"orders": execution_orders_count}
    )

    add_check(
        checks,
        "execution",
        "simulated_plan_present",
        "OK" if isinstance(execution_plan_sim, dict) else "WARNING",
        blocking=False,
        details={"simulated_orders": simulated_orders_count}
    )

    add_check(
        checks,
        "execution",
        "open_positions_present",
        "OK" if open_positions_count >= 0 else "WARNING",
        blocking=False,
        details={"open_positions": open_positions_count}
    )

    governance_status = governance.get("status")
    governance_mode = governance.get("mode") or governance.get("governance_mode")
    action_policy = governance.get("action_policy") or governance.get("policy")
    hard_block = bool(governance.get("hard_block", False))

    add_check(
        checks,
        "governance",
        "governance_artifact_status",
        "OK" if governance_status in ("ok", "OK", None) else "WARNING",
        blocking=False,
        details={"status": governance_status}
    )

    add_check(
        checks,
        "governance",
        "action_policy_present",
        "OK" if action_policy else "WARNING",
        blocking=False,
        details={"action_policy": action_policy}
    )

    add_check(
        checks,
        "governance",
        "hard_block_state",
        "OK" if not hard_block else "BLOCKING",
        blocking=hard_block,
        details={"hard_block": hard_block, "mode": governance_mode}
    )

    risk_mode = risk_limits.get("mode")
    max_positions = risk_limits.get("max_positions")
    size_factor = risk_limits.get("size_factor")
    worst_llm_status = worst_trades_summary.get("llm_status")
    worst_metrics = worst_trades_summary.get("metrics", {}) if isinstance(worst_trades_summary, dict) else {}

    add_check(
        checks,
        "risk",
        "risk_limits_present",
        "OK" if isinstance(risk_limits, dict) and len(risk_limits) > 0 else "WARNING",
        blocking=False,
        details={
            "mode": risk_mode,
            "max_positions": max_positions,
            "size_factor": size_factor,
        }
    )

    add_check(
        checks,
        "risk",
        "risk_mode_safe",
        "OK" if risk_mode in ("reduced", "normal", "safe", "protected", None) else "WARNING",
        blocking=False,
        details={"mode": risk_mode}
    )

    add_check(
        checks,
        "risk",
        "worst_trades_summary_available",
        "OK" if isinstance(worst_trades_summary, dict) and len(worst_trades_summary) > 0 else "WARNING",
        blocking=False,
        details={
            "llm_status": worst_llm_status,
            "n_worst": worst_metrics.get("n_worst"),
            "total_pnl_eur": worst_metrics.get("total_pnl_eur"),
        }
    )

    api_routes = [
        "/dashboard/v3",
        "/api/portfolio_state",
        "/portfolio-target",
        "/api/portfolio/orchestration-status",
        "/api/portfolio/orchestration-consistency",
        "/portfolio/global-preprod-long-run-daily-check",
    ]

    for route in api_routes:
        result = http_ok(route)
        add_check(
            checks,
            "api",
            f"api_route_{route}",
            "OK" if result.get("ok") else "BLOCKING",
            blocking=not bool(result.get("ok")),
            details=result,
        )

    ui_dist_exists = UI_DIST.exists() and UI_DIST.is_dir()
    control_room_src_exists = CONTROL_ROOM_SRC.exists()

    try:
        control_room_txt = CONTROL_ROOM_SRC.read_text(encoding="utf-8") if control_room_src_exists else ""
    except Exception:
        control_room_txt = ""

    ui_has_orch_badge = "ORCH {orchestrationStatus}" in control_room_txt
    ui_has_orch_tone = "orchestrationTone" in control_room_txt

    add_check(
        checks,
        "ui",
        "react_dist_exists",
        "OK" if ui_dist_exists else "BLOCKING",
        blocking=not ui_dist_exists,
        details={"path": str(UI_DIST)}
    )

    add_check(
        checks,
        "ui",
        "control_room_source_exists",
        "OK" if control_room_src_exists else "BLOCKING",
        blocking=not control_room_src_exists,
        details={"path": str(CONTROL_ROOM_SRC)}
    )

    add_check(
        checks,
        "ui",
        "control_room_orch_badge_present",
        "OK" if ui_has_orch_badge else "BLOCKING",
        blocking=not ui_has_orch_badge,
        details={"ui_has_orch_badge": ui_has_orch_badge}
    )

    add_check(
        checks,
        "ui",
        "control_room_orch_tone_present",
        "OK" if ui_has_orch_tone else "WARNING",
        blocking=False,
        details={"ui_has_orch_tone": ui_has_orch_tone}
    )

    blocking_checks = [c for c in checks if c["blocking"]]
    warning_checks = [c for c in checks if c["status"] == "WARNING"]

    governance_checks = [c for c in checks if c["domain"] == "governance"]
    risk_checks = [c for c in checks if c["domain"] == "risk"]
    orchestration_checks = [c for c in checks if c["domain"] == "orchestration"]
    funding_checks = [c for c in checks if c["domain"] == "funding"]
    execution_checks = [c for c in checks if c["domain"] == "execution"]
    api_checks = [c for c in checks if c["domain"] == "api"]
    ui_checks = [c for c in checks if c["domain"] == "ui"]

    governance_domain_status = "BLOCKING" if any(c["blocking"] for c in governance_checks) else ("WARNING" if any(c["status"] == "WARNING" for c in governance_checks) else "OK")
    risk_domain_status = "BLOCKING" if any(c["blocking"] for c in risk_checks) else ("WARNING" if any(c["status"] == "WARNING" for c in risk_checks) else "OK")
    orchestration_domain_status = "BLOCKING" if any(c["blocking"] for c in orchestration_checks) else ("WARNING" if any(c["status"] == "WARNING" for c in orchestration_checks) else "OK")
    funding_domain_status = "BLOCKING" if any(c["blocking"] for c in funding_checks) else ("WARNING" if any(c["status"] == "WARNING" for c in funding_checks) else "OK")
    execution_domain_status = "BLOCKING" if any(c["blocking"] for c in execution_checks) else ("WARNING" if any(c["status"] == "WARNING" for c in execution_checks) else "OK")
    api_domain_status = "BLOCKING" if any(c["blocking"] for c in api_checks) else ("WARNING" if any(c["status"] == "WARNING" for c in api_checks) else "OK")
    ui_domain_status = "BLOCKING" if any(c["blocking"] for c in ui_checks) else ("WARNING" if any(c["status"] == "WARNING" for c in ui_checks) else "OK")

    domains = {
        "governance": {"status": governance_domain_status, "blocking": any(c["blocking"] for c in governance_checks)},
        "risk": {"status": risk_domain_status, "blocking": any(c["blocking"] for c in risk_checks)},
        "execution": {"status": execution_domain_status, "blocking": any(c["blocking"] for c in execution_checks)},
        "funding": {"status": funding_domain_status, "blocking": any(c["blocking"] for c in funding_checks)},
        "orchestration": {
            "status": orchestration_domain_status,
            "blocking": bool(blocking_checks),
        },
        "ui": {"status": ui_domain_status, "blocking": any(c["blocking"] for c in ui_checks)},
        "api": {"status": api_domain_status, "blocking": any(c["blocking"] for c in api_checks)},
    }

    payload = {
        "status": "ok" if not blocking_checks else "error",
        "engine": "global_orchestration_audit_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "global_status": "BLOCKING" if blocking_checks else "OK",
        "alert_level": "BLOCKING" if blocking_checks else "OK",
        "blocking": bool(blocking_checks),
        "domains": domains,
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "ok_checks": len([c for c in checks if c["status"] == "OK"]),
            "warning_checks": len(warning_checks),
            "blocking_checks": len(blocking_checks),
        },
        "reasons": [c["name"] for c in blocking_checks] or ["all_orchestration_checks_ok"],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
