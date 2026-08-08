from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
PREPROD = Path("/opt/nsc/data/preprod")

OUTPUT = DATA / "audits/governance_risk_master_audit.json"

PATHS = {
    "capital_context": DATA / "capital/config/capital_context.json",
    "portfolio_target": PREPROD / "portfolio/portfolio_target.json",
    "portfolio_state": PREPROD / "portfolio/state/portfolio_state.json",
    "governance_crypto": PREPROD / "analysis/governance_engine_pro.json",
    "risk_engine_crypto": PREPROD / "analysis/risk_engine_pro.json",
    "kill_switch_crypto": PREPROD / "trading/kill_switch.json",
    "execution_plan_crypto": PREPROD / "trading/execution_plan.json",
    "offensive_governance": PREPROD / "equities_offensive/governance/governance_engine_pro.json",
    "offensive_state": PREPROD / "equities_offensive/state/state.json",
    "capital_funding_audit": DATA / "audits/capital_funding_master_audit.json",
    "dashboard_v4_audit": DATA / "audits/dashboard_v4_coherence_audit.json",
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


docs = {k: read_json(p, {}) or {} for k, p in PATHS.items()}

failed = []

context = docs["capital_context"]
target = docs["portfolio_target"]
state = docs["portfolio_state"]
crypto_gov = docs["governance_crypto"]
crypto_risk = docs["risk_engine_crypto"]
crypto_kill = docs["kill_switch_crypto"]
crypto_exec = docs["execution_plan_crypto"]
off_gov = docs["offensive_governance"]
off_state = docs["offensive_state"]
capital_audit = docs["capital_funding_audit"]
dashboard_audit = docs["dashboard_v4_audit"]

# =========================================================
# PREPROD / NO REAL MONEY
# =========================================================

if context.get("environment") != "PREPROD":
    failed.append({
        "check": "environment_preprod",
        "severity": "critical",
        "detail": "Capital context must remain PREPROD.",
        "evidence": context.get("environment"),
    })

if context.get("real_money_enabled") is not False:
    failed.append({
        "check": "real_money_disabled",
        "severity": "critical",
        "detail": "Real money must remain disabled in current preprod.",
        "evidence": context.get("real_money_enabled"),
    })

# =========================================================
# PORTFOLIO TARGET / STATE HEALTH
# =========================================================

if target.get("status") != "ok":
    failed.append({
        "check": "portfolio_target_ok",
        "severity": "critical",
        "detail": "Portfolio target must be status=ok.",
        "evidence": target.get("status"),
    })

if state.get("status") != "ok":
    failed.append({
        "check": "portfolio_state_ok",
        "severity": "critical",
        "detail": "Portfolio state must be status=ok.",
        "evidence": state.get("status"),
    })

if target.get("portfolio_regime") != state.get("portfolio_regime"):
    failed.append({
        "check": "target_state_regime_match",
        "severity": "warning",
        "detail": "Portfolio target/state regimes should match.",
        "evidence": {
            "target": target.get("portfolio_regime"),
            "state": state.get("portfolio_regime"),
        },
    })

# =========================================================
# EXECUTION SAFETY
# =========================================================

crypto_policy = crypto_exec.get("action_policy") or crypto_exec.get("execution_mode")

if crypto_policy is None:
    orders = crypto_exec.get("orders") or []
    order_modes = sorted({
        str(o.get("execution_mode") or o.get("action") or "")
        for o in orders
        if isinstance(o, dict) and (o.get("execution_mode") or o.get("action"))
    })
    if order_modes and all(m in {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "SIMULATED_AND_PAPER"} for m in order_modes):
        crypto_policy = ",".join(order_modes)

allowed_crypto_modes = {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "SIMULATED_AND_PAPER"}

if not crypto_policy or not all(m in allowed_crypto_modes for m in str(crypto_policy).split(",")):
    failed.append({
        "check": "crypto_execution_simulated",
        "severity": "critical",
        "detail": "Crypto execution must remain simulated/paper.",
        "evidence": crypto_policy,
    })

off_policy = (
    off_gov.get("action_policy")
    or off_gov.get("execution_mode")
    or off_state.get("ui", {}).get("action_policy")
    or off_state.get("action_policy")
)

if off_policy not in {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "SIMULATED_AND_PAPER", None}:
    failed.append({
        "check": "offensive_execution_simulated",
        "severity": "critical",
        "detail": "Offensive execution must remain simulated/paper.",
        "evidence": off_policy,
    })

# =========================================================
# KILL SWITCH / GOVERNANCE
# =========================================================

kill_status = (
    crypto_kill.get("status")
    or crypto_kill.get("mode")
    or crypto_kill.get("state")
)

hard_block = (
    crypto_kill.get("hard_block")
    or crypto_risk.get("hard_block")
    or crypto_gov.get("hard_block")
)

if hard_block is True:
    orders = crypto_exec.get("orders") or []
    if len(orders) > 0:
        failed.append({
            "check": "hard_block_blocks_orders",
            "severity": "critical",
            "detail": "Hard block active but crypto execution plan still has orders.",
            "evidence": {
                "orders": len(orders),
                "kill_status": kill_status,
            },
        })

# =========================================================
# MASTER AUDITS DEPENDENCIES
# =========================================================

if capital_audit.get("status") != "ok":
    failed.append({
        "check": "capital_funding_audit_ok",
        "severity": "critical",
        "detail": "Capital Funding Master Audit must be ok.",
        "evidence": capital_audit.get("status"),
    })

if dashboard_audit.get("status") != "ok":
    failed.append({
        "check": "dashboard_v4_audit_ok",
        "severity": "warning",
        "detail": "Dashboard V4 Coherence Audit should be ok.",
        "evidence": dashboard_audit.get("status"),
    })

# =========================================================
# STATUS
# =========================================================

status = "ok"
if any(f["severity"] == "critical" for f in failed):
    status = "critical"
elif failed:
    status = "warning"

summary = {
    "environment": context.get("environment"),
    "capital_mode": context.get("capital_mode"),
    "real_money_enabled": context.get("real_money_enabled"),
    "portfolio_regime": target.get("portfolio_regime"),
    "target_total_weight": target.get("total_final_weight"),
    "cash_buffer": target.get("cash_buffer"),
    "crypto_execution_policy": crypto_policy,
    "offensive_execution_policy": off_policy,
    "crypto_kill_status": kill_status,
    "hard_block": bool(hard_block),
    "capital_funding_audit": capital_audit.get("status"),
    "dashboard_v4_audit": dashboard_audit.get("status"),
}

result = {
    "generated_at": utc_now(),
    "status": status,
    "engine": "governance_risk_master_audit_v1",
    "master_intent": {
        "mission": "Validate NSC governance, risk, kill-switch and execution safety before production-like preprod.",
        "rules": [
            "preprod_virtual_only",
            "no_real_money",
            "simulated_execution_only",
            "hard_block_must_block_orders",
            "target_state_alignment",
            "capital_guardrails_required",
            "dashboard_coherence_required"
        ]
    },
    "summary": summary,
    "failed_checks": failed,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": status,
    "summary": summary,
    "failed_checks": failed,
}, indent=2, ensure_ascii=False))
