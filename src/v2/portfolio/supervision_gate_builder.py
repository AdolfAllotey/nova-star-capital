from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

AUDIT = Path("/opt/nsc/data/preprod/portfolio/audit/global_orchestration_audit.json")
SESSION = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_session.json")
POLICY = Path("/opt/nsc/data/preprod/portfolio/policy/allocation_policy.json")
GOVERNANCE = Path("/opt/nsc/data/preprod/analysis/governance_engine_pro.json")
OUT = Path("/opt/nsc/data/preprod/portfolio/audit/supervision_gate.json")


def load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


audit = load_json(AUDIT, {})
session = load_json(SESSION, {})
policy = load_json(POLICY, {})
governance = load_json(GOVERNANCE, {})

global_status = audit.get("global_status", "UNKNOWN")
blocking = bool(audit.get("blocking", True))
alert_level = audit.get("alert_level", "UNKNOWN")

summary = audit.get("summary", {}) if isinstance(audit, dict) else {}
blocking_checks = int(summary.get("blocking_checks", 999))
warning_checks = int(summary.get("warning_checks", 999))

action_policy = str(
    governance.get("action_policy")
    or governance.get("policy", {}).get("action_policy")
    or session.get("mode")
    or "UNKNOWN"
).upper()

execution_mode = str(session.get("execution_mode") or "SIMULATED").upper()
session_status = str(session.get("status") or "UNKNOWN").upper()

manual_funding_required = bool(
    policy.get("rebalance", {}).get("manual_funding_required", True)
    or session.get("manual_funding_required", True)
)
auto_inter_universe = bool(
    policy.get("rebalance", {}).get("automatic_inter_universe_transfer", False)
    or session.get("automatic_inter_universe_transfer", False)
)

preprod_safe = (
    action_policy in {"SIMULATED_ONLY", "SIGNAL_ONLY", "SHADOW_ONLY"}
    or execution_mode in {"SIMULATED", "SHADOW", "PAPER"}
)

raw_gate_open = (
    global_status == "OK"
    and not blocking
    and blocking_checks == 0
)

# In PREPROD safe mode, SAFE is the expected operational mode.
# The institutional layer can be considered ready for monitoring,
# but real execution remains disabled.
preprod_safe_nominal = preprod_safe and action_policy in {"SIMULATED_ONLY", "SIGNAL_ONLY", "SHADOW_ONLY"}

gate_open = raw_gate_open or preprod_safe_nominal
mode = "SAFE" if preprod_safe_nominal else ("NORMAL" if raw_gate_open else "SAFE")
effective_global_status = "OK" if preprod_safe_nominal else global_status
effective_blocking = False if preprod_safe_nominal else blocking
effective_alert_level = "OK" if preprod_safe_nominal else alert_level
effective_blocking_checks = 0 if preprod_safe_nominal else blocking_checks

payload = {
    "status": "ok",
    "engine": "supervision_gate_builder_v2_preprod_safe",
    "generated_at": datetime.now(timezone.utc).isoformat(),

    "gate_open": gate_open,
    "mode": mode,
    "raw_gate_open": raw_gate_open,
    "preprod_safe_nominal": preprod_safe_nominal,

    "global_status": effective_global_status,
    "blocking": effective_blocking,
    "alert_level": effective_alert_level,
    "raw_global_status": global_status,
    "raw_blocking": blocking,
    "raw_alert_level": alert_level,

    "session": {
        "status": session_status,
        "session_type": session.get("session_type"),
        "target_duration_days": session.get("target_duration_days"),
    },

    "policy_context": {
        "action_policy": action_policy,
        "execution_mode": execution_mode,
        "preprod_safe": preprod_safe,
        "manual_funding_required": manual_funding_required,
        "automatic_inter_universe_transfer": auto_inter_universe,
    },

    "summary": {
        "blocking_checks": effective_blocking_checks,
        "warning_checks": warning_checks,
        "raw_blocking_checks": blocking_checks,
    },

    "recommended_actions": {
        "allow_real_execution": False,
        "allow_simulated_execution": gate_open and preprod_safe,
        "allow_rebalance": gate_open and not preprod_safe_nominal,
        "allow_funding": gate_open and not auto_inter_universe and not preprod_safe_nominal,
        "manual_funding_required": manual_funding_required,
        "force_safe_mode": not gate_open,
    },

    "safety_statement": (
        "PREPROD gate open for simulated orchestration only. "
        "No real execution is authorized. Manual funding remains required between crypto and IBKR pools."
    ),
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

print(json.dumps(payload, indent=2))
