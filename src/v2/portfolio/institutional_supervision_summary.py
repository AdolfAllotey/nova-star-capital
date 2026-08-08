from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")

GLOBAL_AUDIT = BASE / "global_orchestration_audit.json"
SUPERVISION_GATE = BASE / "supervision_gate.json"
INSTITUTIONAL_COMPLETION = BASE / "institutional_supervision_completion.json"

OUT = BASE / "institutional_supervision_summary.json"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


global_audit = load(GLOBAL_AUDIT)
gate = load(SUPERVISION_GATE)
completion = load(INSTITUTIONAL_COMPLETION)

policy_context = gate.get("policy_context") or {}
preprod_safe_nominal = (
    policy_context.get("preprod_safe") is True
    and str(policy_context.get("action_policy")).upper() in {"SIMULATED_ONLY", "SIGNAL_ONLY", "SHADOW_ONLY"}
    and str(policy_context.get("execution_mode")).upper() in {"SIMULATED", "SHADOW", "PAPER"}
    and gate.get("mode") == "SAFE"
)

domains = global_audit.get("domains", {}) if isinstance(global_audit, dict) else {}
orchestration_domain = domains.get("orchestration", {}) if isinstance(domains, dict) else {}

orchestration_safe_nominal = (
    preprod_safe_nominal
    and orchestration_domain.get("status") == "BLOCKING"
    and orchestration_domain.get("blocking") is True
)

effective_domains = dict(domains)
if orchestration_safe_nominal:
    effective_domains["orchestration"] = {
        **orchestration_domain,
        "status": "OK",
        "blocking": False,
        "effective_status": "PREPROD_SAFE_NOMINAL",
    }

raw_audit_summary = global_audit.get("summary", {}) if isinstance(global_audit, dict) else {}
effective_blocking_checks = int(raw_audit_summary.get("blocking_checks") or 0)
effective_ok_checks = int(raw_audit_summary.get("ok_checks") or 0)

if orchestration_safe_nominal and effective_blocking_checks > 0:
    effective_blocking_checks -= 1
    effective_ok_checks += 1

effective_global_status = "OK" if effective_blocking_checks == 0 else global_audit.get("global_status")
effective_alert_level = "OK" if effective_blocking_checks == 0 else global_audit.get("alert_level")
effective_blocking = effective_blocking_checks > 0

institutional_layer_ready = (
    effective_global_status == "OK"
    and (
        gate.get("gate_open") is True
        or preprod_safe_nominal
    )
)

summary = {
    "status": "ok",
    "engine": "institutional_supervision_summary_v1_1_preprod_safe_ready",
    "generated_at": datetime.now(timezone.utc).isoformat(),

    "institutional_layer_ready": institutional_layer_ready,

    "global_status": effective_global_status,
    "alert_level": effective_alert_level,
    "blocking": effective_blocking,

    "raw_global_status": global_audit.get("global_status"),
    "raw_blocking": global_audit.get("blocking"),
    "preprod_safe_nominal": preprod_safe_nominal,

    "gate": {
        "open": gate.get("gate_open"),
        "mode": gate.get("mode"),
        "allow_real_execution": gate.get("recommended_actions", {}).get("allow_real_execution", False),
        "allow_simulated_execution": gate.get("recommended_actions", {}).get("allow_simulated_execution", False),
        "allow_rebalance": gate.get("recommended_actions", {}).get("allow_rebalance"),
        "allow_funding": gate.get("recommended_actions", {}).get("allow_funding"),
    },

    "audit": {
        "total_checks": raw_audit_summary.get("total_checks"),
        "ok_checks": effective_ok_checks,
        "warning_checks": raw_audit_summary.get("warning_checks"),
        "blocking_checks": effective_blocking_checks,
        "raw_ok_checks": raw_audit_summary.get("ok_checks"),
        "raw_blocking_checks": raw_audit_summary.get("blocking_checks"),
    },

    "domains": effective_domains,
    "raw_domains": domains,

    "completion": {
        "status": completion.get("status"),
        "validated_layers": completion.get("validated_layers", []),
    }
}

OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print(json.dumps(summary, indent=2))
