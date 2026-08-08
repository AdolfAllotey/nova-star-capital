from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")

OUTPUT = DATA / "audits/runtime_consistency_audit.json"

PATHS = {
    "portfolio_target": PREPROD / "portfolio/portfolio_target.json",
    "portfolio_state": PREPROD / "portfolio/state/portfolio_state.json",
    "execution_plan": PREPROD / "trading/execution_plan.json",
    "open_positions": PREPROD / "trading/open_positions.json",
    "governance": PREPROD / "analysis/governance_engine_pro.json",
    "risk_engine": PREPROD / "analysis/risk_engine_pro.json",
    "kill_switch": PREPROD / "trading/kill_switch.json",
    "health_report": DATA / "audits/preprod_daily_health_report.json",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": str(exc), "__path__": str(path)}


def as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("positions", "orders", "items", "data", "signals"):
            if isinstance(value.get(key), list):
                return value.get(key)
    return []


def severity_status(failed):
    if any(x.get("severity") == "critical" for x in failed):
        return "critical"
    if failed:
        return "warning"
    return "ok"


docs = {name: read_json(path, {}) or {} for name, path in PATHS.items()}

target = docs["portfolio_target"]
state = docs["portfolio_state"]
execution_plan = docs["execution_plan"]
open_positions_doc = docs["open_positions"]
governance = docs["governance"]
risk_engine = docs["risk_engine"]
kill_switch = docs["kill_switch"]
health_report = docs["health_report"]

failed = []

target_weights = target.get("final_brick_weights") or {}
state_bricks = state.get("bricks") or {}

orders = as_list(execution_plan.get("orders") if isinstance(execution_plan, dict) else execution_plan)
open_positions = as_list(open_positions_doc)

# =========================================================
# 1. Target / State regime coherence
# =========================================================

target_regime = target.get("portfolio_regime") or target.get("regime")
state_regime = state.get("portfolio_regime") or state.get("regime")

if target_regime != state_regime:
    failed.append({
        "check": "target_state_regime_match",
        "severity": "warning",
        "detail": "Portfolio target and portfolio state regimes should match.",
        "evidence": {
            "target_regime": target_regime,
            "state_regime": state_regime,
        },
    })

# =========================================================
# 2. Target / State weights coherence
# =========================================================

for brick, target_weight in target_weights.items():
    state_brick = state_bricks.get(brick) or {}
    state_weight = state_brick.get("target_weight_snapshot")

    if state_weight is None:
        failed.append({
            "check": "state_contains_target_brick",
            "severity": "warning",
            "detail": "Portfolio state missing brick from target.",
            "evidence": {
                "brick": brick,
                "target_weight": target_weight,
            },
        })
        continue

    diff = abs(float(target_weight or 0) - float(state_weight or 0))

    if diff > 0.001:
        failed.append({
            "check": "target_state_weight_match",
            "severity": "warning",
            "detail": "Target final weight and state target snapshot differ.",
            "evidence": {
                "brick": brick,
                "target_weight": target_weight,
                "state_weight": state_weight,
                "diff": round(diff, 6),
            },
        })

# =========================================================
# 3. Kill-switch / execution coherence
# =========================================================

hard_block = (
    kill_switch.get("hard_block") is True
    or governance.get("hard_block") is True
    or risk_engine.get("hard_block") is True
)

if hard_block and len(orders) > 0:
    failed.append({
        "check": "hard_block_blocks_orders",
        "severity": "critical",
        "detail": "Hard block active while execution plan contains orders.",
        "evidence": {
            "orders": len(orders),
            "kill_switch_hard_block": kill_switch.get("hard_block"),
            "governance_hard_block": governance.get("hard_block"),
            "risk_hard_block": risk_engine.get("hard_block"),
        },
    })

# =========================================================
# 4. Execution policy coherence
# =========================================================

order_modes = sorted({
    str(o.get("execution_mode") or o.get("action_policy") or "")
    for o in orders
    if isinstance(o, dict) and (o.get("execution_mode") or o.get("action_policy"))
})

unsafe_modes = [
    m for m in order_modes
    if m not in {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "SIMULATED_AND_PAPER"}
]

if unsafe_modes:
    failed.append({
        "check": "orders_execution_policy_safe",
        "severity": "critical",
        "detail": "Execution plan contains unsafe execution modes.",
        "evidence": {
            "order_modes": order_modes,
            "unsafe_modes": unsafe_modes,
        },
    })

# =========================================================
# 5. Open positions coherence
# =========================================================

positions_count = len(open_positions)

if positions_count == 0:
    active_state_weights = {
        name: b.get("current_weight_estimate")
        for name, b in state_bricks.items()
        if isinstance(b, dict) and float(b.get("current_weight_estimate") or 0) > 0
    }

    # In current PREPROD, current_weight_estimate is still signal-derived.
    # This is not critical, but should be visible.
    if active_state_weights:
        failed.append({
            "check": "state_weights_signal_derived_without_positions",
            "severity": "warning",
            "detail": "State has current_weight_estimate > 0 while open_positions is empty; acceptable if signal_derived.",
            "evidence": active_state_weights,
        })

# =========================================================
# 6. Health report coherence
# =========================================================

health_status = health_report.get("status")
daily_decision = (health_report.get("daily_decision") or {}).get("decision")

if health_status not in {"ok", "warning", "critical"}:
    failed.append({
        "check": "health_report_status_valid",
        "severity": "warning",
        "detail": "Health report status is missing or unexpected.",
        "evidence": health_status,
    })

if health_status == "critical" and daily_decision != "STOP_AND_FIX":
    failed.append({
        "check": "health_report_decision_consistency",
        "severity": "critical",
        "detail": "Critical health report should lead to STOP_AND_FIX.",
        "evidence": {
            "health_status": health_status,
            "daily_decision": daily_decision,
        },
    })

# =========================================================
# Output
# =========================================================

summary = {
    "target_regime": target_regime,
    "state_regime": state_regime,
    "target_weights": target_weights,
    "state_bricks_count": len(state_bricks),
    "orders_count": len(orders),
    "open_positions_count": positions_count,
    "order_modes": order_modes,
    "hard_block": bool(hard_block),
    "health_report_status": health_status,
    "health_daily_decision": daily_decision,
}

result = {
    "generated_at": utc_now(),
    "status": severity_status(failed),
    "engine": "runtime_consistency_audit_v1",
    "summary": summary,
    "failed_checks": failed,
    "notes": [
        "V1 checks target/state/governance/execution/runtime coherence.",
        "Signal-derived current weights may produce warnings until broker-reconciled state is available.",
    ],
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": result["status"],
    "summary": summary,
    "failed_checks": failed,
}, indent=2, ensure_ascii=False))
