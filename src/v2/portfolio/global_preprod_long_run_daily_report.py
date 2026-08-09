from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
OUT = BASE / "global_preprod_long_run_daily_report.json"

FILES = {
    "session": BASE / "global_preprod_session.json",
    "daily_check": BASE / "global_preprod_long_run_daily_check.json",
    "orchestration_audit": BASE / "global_orchestration_audit.json",
    "supervision_gate": BASE / "supervision_gate.json",
    "institutional_supervision": BASE / "institutional_supervision_summary.json",
    "long_run_readiness": BASE / "global_preprod_long_run_readiness.json",
    "trend_monitor": BASE / "global_preprod_trend_monitor.json",
    "anomaly_detector": BASE / "global_preprod_anomaly_detector.json",
    "stress_tests": BASE / "global_preprod_stress_test_report.json",
}


def load(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}



def compute_long_run_progress(session):
    started_raw = session.get("started_at") or session.get("generated_at")
    target_days = int(session.get("target_duration_days") or 30)

    # fallback: session created manually after 48h shadow
    if not started_raw:
        started_raw = "2026-05-19T11:17:53+00:00"

    try:
        started_at = datetime.fromisoformat(str(started_raw).replace("Z", "+00:00"))
    except Exception:
        started_at = datetime(2026, 5, 19, 11, 17, 53, tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    elapsed_days_float = max(0.0, (now - started_at).total_seconds() / 86400)
    current_day = min(target_days, int(elapsed_days_float) + 1)
    progress_pct = min(100.0, round((elapsed_days_float / target_days) * 100, 2))

    phases = [
        {"name": "J1-J10 Robustesse", "start_day": 1, "end_day": 10, "focus": "Stabilité runtime, zéro échec pipeline, cohérence API/UI."},
        {"name": "J11-J20 Stratégie", "start_day": 11, "end_day": 20, "focus": "Qualité des signaux, pertinence des allocations, drift contrôlé."},
        {"name": "J21-J30 Risk & Governance", "start_day": 21, "end_day": 30, "focus": "Caps, veto, supervision gate, stress et anomalies."},
        {"name": "J31-J40 Funding & Rebalance", "start_day": 31, "end_day": 40, "focus": "Séparation crypto/IBKR, funding manuel, rebalance gouverné."},
        {"name": "J41-J50 Performance & Explainability", "start_day": 41, "end_day": 50, "focus": "Lecture PnL, décisions explicables, non-actions justifiées."},
        {"name": "J51-J60 Production Readiness", "start_day": 51, "end_day": 60, "focus": "Audit final, checklists, décision go/no-go production."},
    ]

    active_phase = next((x for x in phases if x["start_day"] <= current_day <= x["end_day"]), phases[-1])

    return {
        "started_at": started_at.isoformat(),
        "target_duration_days": target_days,
        "elapsed_days": round(elapsed_days_float, 2),
        "current_day": current_day,
        "progress_pct": progress_pct,
        "active_phase": active_phase,
        "phases": phases,
    }


data = {name: load(path, {}) for name, path in FILES.items()}

session = data["session"]
progress = compute_long_run_progress(session)
daily = data["daily_check"]
audit = data["orchestration_audit"]
gate = data["supervision_gate"]
institutional = data["institutional_supervision"]
trend = data["trend_monitor"]
anomaly = data["anomaly_detector"]
stress = data["stress_tests"]

daily_summary = daily.get("summary", {})
audit_summary = audit.get("summary", {})
institutional_audit = institutional.get("audit") or {}
institutional_gate = institutional.get("gate") or {}
gate_actions = gate.get("recommended_actions", {})

preprod_safe_nominal = (
    institutional.get("preprod_safe_nominal") is True
    or gate.get("preprod_safe_nominal") is True
)

failed_daily = int(daily_summary.get("failed", 0) or 0)

if preprod_safe_nominal:
    audit_blocking = int(institutional_audit.get("blocking_checks", 0) or 0)
    audit_warnings = int(institutional_audit.get("warning_checks", 0) or 0)
    blocking = bool(institutional.get("blocking", False))
else:
    audit_blocking = int(audit_summary.get("blocking_checks", 0) or 0)
    audit_warnings = int(audit_summary.get("warning_checks", 0) or 0)
    blocking = bool(audit.get("blocking"))

allow_simulated_execution = (
    gate_actions.get("allow_simulated_execution") is True
    or institutional_gate.get("allow_simulated_execution") is True
)

allow_real_execution = (
    gate_actions.get("allow_real_execution") is True
    or institutional_gate.get("allow_real_execution") is True
)

gate_open_effective = (
    gate.get("gate_open") is True
    or institutional_gate.get("open") is True
)

status = "OK"
if blocking or failed_daily > 0 or audit_blocking > 0:
    status = "BLOCKING"
elif audit_warnings > 0:
    status = "WARNING"

payload = {
    "status": status.lower(),
    "engine": "global_preprod_long_run_daily_report_v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "session": {
        "status": session.get("status"),
        "session_type": session.get("session_type"),
        "target_duration_days": session.get("target_duration_days"),
        "mode": session.get("mode"),
        "execution_mode": session.get("execution_mode"),
    },
    "progress": progress,
  "headline": {
        "global_status": status,
        "can_continue_long_run": status in ("OK", "WARNING") and allow_simulated_execution,
        "requires_intervention": status == "BLOCKING",
        "real_execution_authorized": bool(allow_real_execution),
        "simulated_execution_authorized": bool(allow_simulated_execution),
        "manual_funding_required": bool(gate_actions.get("manual_funding_required", True)),
    },
    "kpis": {
        "daily_checks_passed": daily_summary.get("passed", 0),
        "daily_checks_failed": failed_daily,
        "orchestration_total_checks": audit_summary.get("total_checks", 0),
        "orchestration_warning_checks": audit_warnings,
        "orchestration_blocking_checks": audit_blocking,
        "gate_open": gate_open_effective,
        "gate_mode": gate.get("mode") or institutional_gate.get("mode"),
        "preprod_safe_nominal": preprod_safe_nominal,
        "trend_status": trend.get("trend_status") or trend.get("status"),
        "anomaly_status": anomaly.get("anomaly_status") or anomaly.get("status"),
        "stress_status": stress.get("status"),
    },
    "safety_statement": gate.get(
        "safety_statement",
        "PREPROD long run remains simulated-only. No real execution is authorized."
    ),
    "decision": {
        "continue_active_preprod_session": status in ("OK", "WARNING"),
        "pause_required": status == "BLOCKING",
        "next_step": "continue_monitoring" if status in ("OK", "WARNING") else "manual_review_required",
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
