from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")

OUTPUT = DATA / "audits/preprod_daily_health_report.json"
TEXT_OUTPUT = DATA / "audits/preprod_daily_health_report.txt"
HISTORY_DIR = DATA / "audits/history/preprod_daily_health"

AUDITS = {
    "preprod_go_nogo": DATA / "audits/preprod_go_nogo_master_audit.json",
    "governance_risk": DATA / "audits/governance_risk_master_audit.json",
    "dashboard_v4": DATA / "audits/dashboard_v4_coherence_audit.json",
    "capital_funding": DATA / "audits/capital_funding_master_audit.json",
    "portfolio_engine": DATA / "audits/portfolio_engine_master_audit.json",
    "runtime_consistency": DATA / "audits/runtime_consistency_audit.json",
    "runtime_telemetry": DATA / "audits/runtime_telemetry_audit.json",
    "dynamic_signal_activity": DATA / "audits/dynamic_signal_activity_audit.json",
}

CORE_ARTIFACTS = {
    "portfolio_target": PREPROD / "portfolio/portfolio_target.json",
    "portfolio_state": PREPROD / "portfolio/state/portfolio_state.json",
    "execution_plan": PREPROD / "trading/execution_plan.json",
    "kill_switch": PREPROD / "trading/kill_switch.json",
    "governance_crypto": PREPROD / "analysis/governance_engine_pro.json",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def file_age_seconds(path):
    try:
        return round(datetime.now().timestamp() - path.stat().st_mtime)
    except Exception:
        return None


def systemctl_is_active(service):
    try:
        result = subprocess.check_output(
            ["systemctl", "is-active", service],
            text=True
        ).strip()
        return result
    except Exception:
        return "unknown"


def get_memory():
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()

        mem_total = None
        mem_available = None

        for line in lines:
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                mem_available = int(line.split()[1])

        if mem_total and mem_available:
            used = mem_total - mem_available
            pct = round((used / mem_total) * 100, 2)

            return {
                "used_percent": pct,
                "total_mb": round(mem_total / 1024),
                "available_mb": round(mem_available / 1024),
            }

    except Exception:
        pass

    return {}


def get_load_average():
    try:
        load1, load5, load15 = os.getloadavg()
        return {
            "1m": round(load1, 2),
            "5m": round(load5, 2),
            "15m": round(load15, 2),
        }
    except Exception:
        return {}


portfolio_target = read_json(CORE_ARTIFACTS["portfolio_target"], {}) or {}
portfolio_state = read_json(CORE_ARTIFACTS["portfolio_state"], {}) or {}
kill_switch = read_json(CORE_ARTIFACTS["kill_switch"], {}) or {}
execution_plan = read_json(CORE_ARTIFACTS["execution_plan"], {}) or {}
governance = read_json(CORE_ARTIFACTS["governance_crypto"], {}) or {}

bricks = portfolio_state.get("bricks") or {}

bricks_summary = {}
brick_drift = {}

for name, brick in bricks.items():
    if not isinstance(brick, dict):
        continue

    target_weight = float(brick.get("target_weight_snapshot") or 0)
    current_weight = float(brick.get("current_weight_estimate") or 0)
    drift = round(current_weight - target_weight, 6)

    if abs(drift) >= 0.05:
        drift_status = "critical"
    elif abs(drift) >= 0.02:
        drift_status = "warning"
    else:
        drift_status = "ok"

    brick_drift[name] = {
        "target_weight": target_weight,
        "current_weight": current_weight,
        "drift": drift,
        "drift_status": drift_status,
    }

    bricks_summary[name] = {
        "status": brick.get("status"),
        "regime": brick.get("regime"),
        "confidence": brick.get("confidence"),
        "portfolio_role": brick.get("portfolio_role"),
        "funding_pool": brick.get("funding_pool"),
        "target_weight_snapshot": brick.get("target_weight_snapshot"),
        "current_weight_estimate": brick.get("current_weight_estimate"),
        "target_amount_eur": brick.get("target_amount_eur"),
        "state_origin": brick.get("state_origin"),
        "risk_flags": brick.get("risk_flags"),
        "drift": drift,
        "drift_status": drift_status,
    }

audit_results = {}
audit_summary = {
    "ok": 0,
    "warning": 0,
    "critical": 0,
    "missing": 0,
}

for name, path in AUDITS.items():
    doc = read_json(path, {"status": "missing"})

    status = str(doc.get("status", "missing")).lower()

    audit_results[name] = {
        "status": status,
        "path": str(path),
    }

    if status in audit_summary:
        audit_summary[status] += 1
    else:
        audit_summary["missing"] += 1


stale_artifacts = []

STALE_RULES_SECONDS = {
    "portfolio_target": 6 * 3600,
    "portfolio_state": 6 * 3600,
    "execution_plan": 2 * 3600,
    "kill_switch": 24 * 3600,
    "governance_crypto": 6 * 3600,
}

for name, path in CORE_ARTIFACTS.items():
    age = file_age_seconds(path)
    threshold = STALE_RULES_SECONDS.get(name, 24 * 3600)

    if age is None:
        stale = True
        severity = "critical"
        reason = "missing_or_unreadable"
    elif age > threshold * 2:
        stale = True
        severity = "critical"
        reason = f"age_seconds_above_critical_threshold_{threshold * 2}"
    elif age > threshold:
        stale = True
        severity = "warning"
        reason = f"age_seconds_above_warning_threshold_{threshold}"
    else:
        stale = False
        severity = "ok"
        reason = "fresh"

    stale_artifacts.append({
        "artifact": name,
        "path": str(path),
        "age_seconds": age,
        "threshold_seconds": threshold,
        "stale": stale,
        "severity": severity,
        "reason": reason,
    })


critical_stale = [x for x in stale_artifacts if x.get("severity") == "critical"]
warning_stale = [x for x in stale_artifacts if x.get("severity") == "warning"]

report_status = "ok"
if critical_stale or audit_summary.get("critical", 0) > 0:
    report_status = "critical"
elif warning_stale or audit_summary.get("warning", 0) > 0:
    report_status = "warning"

critical_drift = [x for x in brick_drift.values() if x.get("drift_status") == "critical"]
warning_drift = [x for x in brick_drift.values() if x.get("drift_status") == "warning"]

if critical_drift:
    report_status = "critical"
elif warning_drift and report_status == "ok":
    report_status = "warning"

daily_decision = {
    "decision": "CONTINUE_PREPROD",
    "severity": report_status,
    "reasons": [],
}

if report_status == "critical":
    daily_decision["decision"] = "STOP_AND_FIX"
    daily_decision["reasons"].append("critical_health_condition_detected")
elif report_status == "warning":
    daily_decision["decision"] = "WATCH"
    daily_decision["reasons"].append("warning_health_condition_detected")
else:
    daily_decision["reasons"].append("all_core_health_checks_ok")

if kill_switch.get("hard_block") is True:
    daily_decision["decision"] = "STOP_AND_FIX"
    daily_decision["severity"] = "critical"
    daily_decision["reasons"].append("kill_switch_hard_block_active")

if governance.get("hard_block") is True:
    daily_decision["decision"] = "STOP_AND_FIX"
    daily_decision["severity"] = "critical"
    daily_decision["reasons"].append("governance_hard_block_active")

report = {
    "status": report_status,
    "engine": "preprod_daily_health_report_v1",
    "timestamp": utc_now(),
    "environment": "PREPROD",

    "system_health": {
        "api_service": systemctl_is_active("nsc-api.service"),
        "kernel_service": systemctl_is_active("nsc-kernel.service"),
        "memory": get_memory(),
        "load_average": get_load_average(),
    },

    "portfolio_health": {
        "portfolio_regime": portfolio_target.get("portfolio_regime"),
        "total_final_weight": portfolio_target.get("total_final_weight"),
        "cash_buffer": portfolio_target.get("cash_buffer"),
        "final_brick_weights": portfolio_target.get("final_brick_weights"),
    },

    "bricks_health": bricks_summary,

    "portfolio_drift": {
        "summary": {
            "critical": len([x for x in brick_drift.values() if x.get("drift_status") == "critical"]),
            "warning": len([x for x in brick_drift.values() if x.get("drift_status") == "warning"]),
            "ok": len([x for x in brick_drift.values() if x.get("drift_status") == "ok"]),
        },
        "bricks": brick_drift,
    },

    "governance_risk": {
        "hard_block": governance.get("hard_block"),
        "kill_switch_status": kill_switch.get("status") or kill_switch.get("mode"),
        "execution_plan_orders": len(execution_plan.get("orders", [])),
    },

    "audit_consolidation": {
        "summary": audit_summary,
        "audits": audit_results,
    },

    "daily_decision": daily_decision,

    "stale_artifacts": stale_artifacts,

    "notes": [
        "V1 consolidates runtime, governance and audit health.",
        "Future versions will add drift detection and runtime telemetry.",
    ],
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

text_lines = [
    "NSC PREPROD DAILY HEALTH REPORT",
    f"Timestamp: {report.get('timestamp')}",
    f"Status: {report.get('status')}",
    f"Decision: {report.get('daily_decision', {}).get('decision')}",
    f"Regime: {report.get('portfolio_health', {}).get('portfolio_regime')}",
    f"Cash buffer: {report.get('portfolio_health', {}).get('cash_buffer')}",
    "",
    "Audits:",
    f"- OK: {audit_summary.get('ok')}",
    f"- WARNING: {audit_summary.get('warning')}",
    f"- CRITICAL: {audit_summary.get('critical')}",
    f"- MISSING: {audit_summary.get('missing')}",
    "",
    "Drift:",
    f"- OK: {report.get('portfolio_drift', {}).get('summary', {}).get('ok')}",
    f"- WARNING: {report.get('portfolio_drift', {}).get('summary', {}).get('warning')}",
    f"- CRITICAL: {report.get('portfolio_drift', {}).get('summary', {}).get('critical')}",
    "",
    "Stale artifacts:",
    f"- OK: {len([x for x in stale_artifacts if x.get('severity') == 'ok'])}",
    f"- WARNING: {len([x for x in stale_artifacts if x.get('severity') == 'warning'])}",
    f"- CRITICAL: {len([x for x in stale_artifacts if x.get('severity') == 'critical'])}",
    "",
    "Bricks:",
]

for name, brick in bricks_summary.items():
    text_lines.append(
        f"- {name}: regime={brick.get('regime')} | confidence={brick.get('confidence')} | "
        f"target={brick.get('target_weight_snapshot')} | drift={brick.get('drift')} | "
        f"status={brick.get('drift_status')}"
    )

TEXT_OUTPUT.write_text("\n".join(text_lines) + "\n", encoding="utf-8")

HISTORY_DIR.mkdir(parents=True, exist_ok=True)
snapshot_name = f"preprod_daily_health_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
snapshot_path = HISTORY_DIR / snapshot_name
snapshot_path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print(json.dumps(report, indent=2, ensure_ascii=False))
print(f"snapshot_written={snapshot_path}")
