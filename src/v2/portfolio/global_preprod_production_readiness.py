from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
OUT = BASE / "global_preprod_production_readiness.json"

FILES = {
    "daily_report": BASE / "global_preprod_long_run_daily_report.json",
    "daily_check": BASE / "global_preprod_long_run_daily_check.json",
    "audit": BASE / "global_orchestration_audit.json",
    "gate": BASE / "supervision_gate.json",
    "session": BASE / "global_preprod_session.json",
}

def load(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}

data = {k: load(v, {}) for k, v in FILES.items()}

daily = data["daily_report"]
check = data["daily_check"]
audit = data["audit"]
gate = data["gate"]

headline = daily.get("headline", {})
kpis = daily.get("kpis", {})
progress = daily.get("progress", {})

blocking = int(kpis.get("orchestration_blocking_checks") or 0)
warnings = int(kpis.get("orchestration_warning_checks") or 0)
daily_failed = int(kpis.get("daily_checks_failed") or 0)
progress_pct = float(progress.get("progress_pct") or 0)

real_execution = bool(headline.get("real_execution_authorized"))
simulated_execution = bool(headline.get("simulated_execution_authorized"))
manual_funding = bool(headline.get("manual_funding_required"))

score = 100
score -= blocking * 25
score -= warnings * 8
score -= daily_failed * 15
score -= 0 if simulated_execution else 20
score -= 50 if real_execution else 0
score = max(0, min(100, score))

if blocking > 0 or daily_failed > 0 or real_execution:
    decision = "NO_GO"
elif score >= 90 and progress_pct >= 100:
    decision = "GO"
elif score >= 85:
    decision = "CONDITIONAL_GO"
else:
    decision = "HOLD"

payload = {
    "status": "ok",
    "engine": "global_preprod_production_readiness_v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "decision": decision,
    "readiness_score": score,
    "progress_pct": progress_pct,
    "current_day": progress.get("current_day"),
    "target_duration_days": progress.get("target_duration_days"),
    "checks": {
        "blocking_checks": blocking,
        "warning_checks": warnings,
        "daily_failed_checks": daily_failed,
        "real_execution_authorized": real_execution,
        "simulated_execution_authorized": simulated_execution,
        "manual_funding_required": manual_funding,
        "gate_open": kpis.get("gate_open"),
        "gate_mode": kpis.get("gate_mode"),
        "trend_status": kpis.get("trend_status"),
        "anomaly_status": kpis.get("anomaly_status"),
        "stress_status": kpis.get("stress_status"),
    },
    "recommendation": (
        "Production not authorized until the 60-day PREPROD cycle is complete."
        if progress_pct < 100
        else "Review final checklist and prepare controlled production decision."
    ),
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
