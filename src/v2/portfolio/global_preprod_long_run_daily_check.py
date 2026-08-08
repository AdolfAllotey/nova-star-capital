from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
GOV = Path("/opt/nsc/data/preprod/analysis/governance_engine_pro.json")
SESSION = BASE / "global_preprod_session.json"
GATE = BASE / "supervision_gate.json"
INSTITUTIONAL = BASE / "institutional_supervision_summary.json"
POLICY = Path("/opt/nsc/data/preprod/portfolio/policy/allocation_policy.json")
OUT = BASE / "global_preprod_long_run_daily_check.json"


def load(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


gov = load(GOV, {})
session = load(SESSION, {})
gate = load(GATE, {})
institutional = load(INSTITUTIONAL, {})
policy = load(POLICY, {})

institutional_gate = institutional.get("gate") or {}
preprod_safe_nominal = (
    institutional.get("preprod_safe_nominal") is True
    or gate.get("preprod_safe_nominal") is True
)

checks = []

def add(name, passed, details):
    checks.append({
        "name": name,
        "passed": bool(passed),
        "details": details,
    })

action_policy = str(gov.get("action_policy") or gov.get("policy", {}).get("action_policy") or "").upper()
caps = gov.get("caps") or {}
gate_actions = gate.get("recommended_actions") or {}
rebalance = policy.get("rebalance") or {}

add("session_active", session.get("status") == "ACTIVE", {
    "status": session.get("status"),
    "session_type": session.get("session_type"),
})

add("simulated_only_policy", action_policy == "SIMULATED_ONLY", {
    "action_policy": action_policy,
})

add("preprod_caps_valid", (
    # PREPROD rule:
    # max_orders_per_run = 0 means unlimited order count.
    # Notional caps remain active and must be positive.
    int(caps.get("max_orders_per_run", 0) or 0) == 0
    and float(caps.get("max_notional_eur_per_run", 0) or 0) > 0
    and float(caps.get("max_notional_eur_per_asset", 0) or 0) > 0
), {
    "caps": caps,
    "rule": "PREPROD: max_orders_per_run=0 unlimited, notional caps positive",
})

add("no_real_execution", gate_actions.get("allow_real_execution") is False, {
    "allow_real_execution": gate_actions.get("allow_real_execution"),
})

add("simulated_execution_allowed", (
    gate_actions.get("allow_simulated_execution") is True
    or institutional_gate.get("allow_simulated_execution") is True
), {
    "allow_simulated_execution": gate_actions.get("allow_simulated_execution"),
    "institutional_allow_simulated_execution": institutional_gate.get("allow_simulated_execution"),
    "preprod_safe_nominal": preprod_safe_nominal,
})

add("manual_funding_required", (
    rebalance.get("manual_funding_required") is True
    and rebalance.get("automatic_inter_universe_transfer") is False
), {
    "manual_funding_required": rebalance.get("manual_funding_required"),
    "automatic_inter_universe_transfer": rebalance.get("automatic_inter_universe_transfer"),
})

passed = sum(1 for c in checks if c["passed"])
failed = len(checks) - passed

payload = {
    "status": "ok" if failed == 0 else "warning",
    "engine": "global_preprod_long_run_daily_check_v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "summary": {
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
    },
    "checks": checks,
    "decision": {
        "can_continue_long_run": failed == 0,
        "requires_intervention": failed > 0,
        "next_step": "continue_60d_global_preprod" if failed == 0 else "review_failed_checks",
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
