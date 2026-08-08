from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
OUTPUT = DATA / "audits/preprod_go_nogo_master_audit.json"

AUDITS = {
    "crypto": DATA / "audits/crypto_master_strategy_audit.json",
    "equities_offensive": DATA / "audits/equities_offensive_master_strategy_audit.json",
    "equities_defensive": DATA / "audits/equities_defensive_master_strategy_audit.json",
    "bonds": DATA / "audits/bonds_master_strategy_audit.json",
    "precious_metals": DATA / "audits/precious_metals_master_strategy_audit.json",
    "options_us": DATA / "audits/options_us_master_strategy_audit.json",
    "long_term_global": DATA / "audits/long_term_global_master_strategy_audit.json",
    "portfolio_engine": DATA / "audits/portfolio_engine_master_audit.json",
    "capital_funding": DATA / "audits/capital_funding_master_audit.json",
    "dashboard_v4": DATA / "audits/dashboard_v4_coherence_audit.json",
    "governance_risk": DATA / "audits/governance_risk_master_audit.json",
    "runtime_consistency": DATA / "audits/runtime_consistency_audit.json",
    "runtime_telemetry": DATA / "audits/runtime_telemetry_audit.json",
    "dynamic_signal_activity": DATA / "audits/dynamic_signal_activity_audit.json",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path):
    try:
        if not path.exists():
            return {"status": "missing", "path": str(path)}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "error", "error": str(exc), "path": str(path)}


audit_results = {name: read_json(path) for name, path in AUDITS.items()}

critical = []
warnings = []
missing = []

for name, doc in audit_results.items():
    status = doc.get("status")

    if status == "ok":
        continue

    if status == "missing":
        missing.append(name)
        critical.append({
            "audit": name,
            "status": status,
            "detail": "Audit file missing.",
            "path": str(AUDITS[name]),
        })
    elif status == "critical":
        critical.append({
            "audit": name,
            "status": status,
            "failed_checks": doc.get("failed_checks", []),
        })
    elif status in {"warning", "warn"}:
        warnings.append({
            "audit": name,
            "status": status,
            "failed_checks": doc.get("failed_checks", []),
        })
    else:
        warnings.append({
            "audit": name,
            "status": status,
            "detail": "Unexpected audit status.",
        })

go_nogo = "GO_FOR_CONTINUED_PREPROD_OBSERVATION"

if critical:
    go_nogo = "NO_GO_FIX_CRITICALS_FIRST"
elif warnings:
    go_nogo = "GO_WITH_WARNINGS"

summary = {
    "audits_total": len(AUDITS),
    "audits_ok": sum(1 for d in audit_results.values() if d.get("status") == "ok"),
    "audits_warning": len(warnings),
    "audits_critical": len(critical),
    "audits_missing": len(missing),
    "go_nogo": go_nogo,
}

result = {
    "generated_at": utc_now(),
    "status": "ok" if not critical else "critical",
    "engine": "preprod_go_nogo_master_audit_v1",
    "summary": summary,
    "audit_statuses": {
        name: doc.get("status") for name, doc in audit_results.items()
    },
    "critical_items": critical,
    "warning_items": warnings,
    "recommendation": (
        "Continue production-like PREPROD observation."
        if not critical
        else "Fix critical items before starting or extending production-like PREPROD."
    ),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": result["status"],
    "summary": summary,
    "audit_statuses": result["audit_statuses"],
    "critical_items": critical,
    "warning_items": warnings,
}, indent=2, ensure_ascii=False))
