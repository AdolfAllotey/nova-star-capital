from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")

GLOBAL_AUDIT = BASE / "global_orchestration_audit.json"
SUPERVISION_GATE = BASE / "supervision_gate.json"
INSTITUTIONAL_COMPLETION = BASE / "institutional_supervision_completion.json"

OUT = BASE / "institutional_supervision_summary.json"


def load_required(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"required_authority_unreadable:{path}") from exc
    if not isinstance(value, dict) or not value:
        raise RuntimeError(f"required_authority_invalid:{path}")
    return value


def load_optional(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


global_audit = load_required(GLOBAL_AUDIT)
gate = load_required(SUPERVISION_GATE)
completion = load_optional(INSTITUTIONAL_COMPLETION)

raw_audit_summary = global_audit.get("summary")
if not isinstance(raw_audit_summary, dict):
    raise RuntimeError("global_audit_summary_invalid")
if "blocking_checks" not in raw_audit_summary:
    raise RuntimeError("global_audit_blocking_checks_missing")

raw_blocking_checks = raw_audit_summary["blocking_checks"]
if isinstance(raw_blocking_checks, bool) or not isinstance(raw_blocking_checks, int):
    raise RuntimeError("global_audit_blocking_checks_invalid")
if raw_blocking_checks < 0:
    raise RuntimeError("global_audit_blocking_checks_invalid")

policy_context = gate.get("policy_context") or {}
preprod_safe_nominal = (
    policy_context.get("preprod_safe") is True
    and str(policy_context.get("action_policy")).upper() in {"SIMULATED_ONLY", "SIGNAL_ONLY", "SHADOW_ONLY"}
    and str(policy_context.get("execution_mode")).upper() in {"SIMULATED", "SHADOW", "PAPER"}
    and gate.get("mode") == "SAFE"
)

domains = global_audit.get("domains")
if not isinstance(domains, dict):
    raise RuntimeError("global_audit_domains_invalid")

effective_domains = dict(domains)
effective_blocking_checks = raw_blocking_checks
effective_ok_checks = int(raw_audit_summary.get("ok_checks") or 0)

effective_global_status = global_audit.get("global_status")
effective_alert_level = global_audit.get("alert_level")
effective_blocking = bool(global_audit.get("blocking", True))

audit_contract_ok = (
    effective_global_status == "OK"
    and effective_blocking is False
    and effective_blocking_checks == 0
)

if not audit_contract_ok:
    effective_blocking = True

institutional_layer_ready = (
    audit_contract_ok
    and gate.get("gate_open") is True
    and gate.get("blocking") is False
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

from src.v2.utils.file_utils import save_json_file_atomic

save_json_file_atomic(OUT, summary)

print(json.dumps(summary, indent=2))
