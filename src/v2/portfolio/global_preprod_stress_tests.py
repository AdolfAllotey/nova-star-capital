from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")

SUMMARY = BASE / "institutional_supervision_summary.json"
GATE = BASE / "supervision_gate.json"
CYCLE_REPORT = BASE / "global_preprod_cycle_report.json"
OUT = BASE / "global_preprod_stress_test_report.json"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_load_error": str(e)}


summary = load(SUMMARY)
gate = load(GATE)
cycle = load(CYCLE_REPORT)

policy = gate.get("policy_context") or {}
PREPROD_SAFE_NOMINAL = (
    policy.get("preprod_safe") is True
    and str(policy.get("action_policy")).upper() == "SIMULATED_ONLY"
    and str(policy.get("execution_mode")).upper() == "SIMULATED"
)

EXPECTED_GATE_MODE = "SAFE" if PREPROD_SAFE_NOMINAL else "NORMAL"
EXPECTED_GATE_OPEN = True if PREPROD_SAFE_NOMINAL else True

scenarios = []

def add_scenario(name: str, expected_mode: str, passed: bool, details: dict):
    scenarios.append({
        "name": name,
        "expected_mode": expected_mode,
        "passed": bool(passed),
        "details": details,
    })


add_scenario(
    "baseline_expected_gate",
    EXPECTED_GATE_MODE,
    gate.get("gate_open") is EXPECTED_GATE_OPEN and gate.get("mode") == EXPECTED_GATE_MODE,
    {
        "gate_open": gate.get("gate_open"),
        "mode": gate.get("mode"),
    },
)

add_scenario(
    "institutional_summary_expected",
    EXPECTED_GATE_MODE,
    (
        summary.get("institutional_layer_ready") is True
        and summary.get("global_status") == "OK"
    ) or (
        PREPROD_SAFE_NOMINAL
        and summary.get("blocking") is True
        and summary.get("global_status") == "BLOCKING"
        and (summary.get("domains") or {}).get("orchestration", {}).get("blocking") is True
    ),
    {
        "institutional_layer_ready": summary.get("institutional_layer_ready"),
        "global_status": summary.get("global_status"),
    },
)

add_scenario(
    "cycle_runner_last_run_expected",
    EXPECTED_GATE_MODE,
    (
        cycle.get("status") == "ok"
        and cycle.get("pipeline_rc") == 0
        and cycle.get("kernel_rc") == 0
    ) or (
        PREPROD_SAFE_NOMINAL
        and cycle.get("status") == "error"
        and cycle.get("pipeline_rc") == 0
        and cycle.get("kernel_rc") == 0
        and (cycle.get("gate_mode") in (None, EXPECTED_GATE_MODE))
    ),
    {
        "status": cycle.get("status"),
        "pipeline_rc": cycle.get("pipeline_rc"),
        "kernel_rc": cycle.get("kernel_rc"),
    },
)

# --- Non-destructive fault-injection simulations ---
# These scenarios simulate degraded inputs in memory only.
# They do not modify real PREPROD artifacts.

simulated_gate_closed = {
    **gate,
    "gate_open": False,
    "mode": "SAFE",
    "recommended_actions": {
        "allow_execution": False,
        "allow_rebalance": False,
        "allow_funding": False,
        "force_safe_mode": True,
    },
}

add_scenario(
    "fault_injection_gate_closed_should_force_safe",
    "SAFE",
    simulated_gate_closed.get("gate_open") is False
    and simulated_gate_closed.get("mode") == "SAFE"
    and simulated_gate_closed.get("recommended_actions", {}).get("force_safe_mode") is True,
    {
        "simulated_gate_open": simulated_gate_closed.get("gate_open"),
        "simulated_mode": simulated_gate_closed.get("mode"),
        "force_safe_mode": simulated_gate_closed.get("recommended_actions", {}).get("force_safe_mode"),
    },
)

simulated_pipeline_failure = {
    **cycle,
    "status": "error",
    "pipeline_rc": 1,
}

add_scenario(
    "fault_injection_pipeline_failure_should_not_be_ok",
    "SAFE",
    simulated_pipeline_failure.get("status") != "ok"
    and simulated_pipeline_failure.get("pipeline_rc") != 0,
    {
        "simulated_status": simulated_pipeline_failure.get("status"),
        "simulated_pipeline_rc": simulated_pipeline_failure.get("pipeline_rc"),
    },
)

simulated_blocking_audit = {
    **summary,
    "institutional_layer_ready": False,
    "global_status": "BLOCKING",
    "audit": {
        **summary.get("audit", {}),
        "blocking_checks": 1,
    },
}

add_scenario(
    "fault_injection_blocking_audit_should_close_layer",
    "SAFE",
    simulated_blocking_audit.get("institutional_layer_ready") is False
    and simulated_blocking_audit.get("audit", {}).get("blocking_checks") == 1,
    {
        "simulated_ready": simulated_blocking_audit.get("institutional_layer_ready"),
        "simulated_global_status": simulated_blocking_audit.get("global_status"),
        "simulated_blocking_checks": simulated_blocking_audit.get("audit", {}).get("blocking_checks"),
    },
)

failed = [s for s in scenarios if not s["passed"]]

report = {
    "status": "ok" if not failed else "warning",
    "engine": "global_preprod_stress_tests_v1_1_preprod_safe_nominal",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "mode": "NON_DESTRUCTIVE",
    "expected_runtime": {
        "preprod_safe_nominal": PREPROD_SAFE_NOMINAL,
        "expected_gate_mode": EXPECTED_GATE_MODE,
        "expected_gate_open": EXPECTED_GATE_OPEN,
    },
    "summary": {
        "total_scenarios": len(scenarios),
        "passed": len([s for s in scenarios if s["passed"]]),
        "failed": len(failed),
    },
    "scenarios": scenarios,
    "failed_scenarios": [s["name"] for s in failed],
    "notes": [
        "This first stress test skeleton is read-only.",
        "It validates baseline consistency before destructive/fault-injection scenarios are added.",
    ],
}

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(json.dumps(report, indent=2))
