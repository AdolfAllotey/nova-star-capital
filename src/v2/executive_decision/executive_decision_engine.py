from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any
import json
import os


BASE = Path(
    os.getenv(
        "NSC_DATA_DIR",
        "/opt/nsc/data/preprod",
    )
)

OUT = BASE / "executive_decision"
CURRENT_PATH = OUT / "executive_decision.json"
HISTORY_DIR = OUT / "history"

PATHS = {
    "portfolio_target": BASE / "portfolio/portfolio_target.json",
    "portfolio_state": BASE / "portfolio/state/portfolio_state.json",
    "rebalance_plan": BASE / "portfolio/rebalance/rebalance_plan.json",
    "allocation_policy": BASE / "portfolio/policy/allocation_policy.json",
    "governance": BASE / "analysis/governance_engine_pro.json",
    "master_coherence": BASE / "portfolio/audit/master_coherence_audit.json",
    "global_orchestration": BASE / "portfolio/audit/global_orchestration_audit.json",
    "supervision_gate": BASE / "portfolio/audit/supervision_gate.json",
    "institutional_supervision": (
        BASE / "portfolio/audit/institutional_supervision_summary.json"
    ),
    "operational_confidence": (
        BASE / "portfolio/audit/operational_confidence.json"
    ),
    "execution_confidence": (
        BASE / "portfolio/audit/execution_confidence.json"
    ),
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 1.0,
) -> float:
    return max(low, min(high, value))


def normalize_confidence(value: Any) -> float:
    result = safe_float(value, 0.0)

    if result > 1.0:
        result = result / 100.0

    return clamp(result)


def file_freshness(
    path: Path,
    max_age_hours: float = 24.0,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "age_hours": None,
            "max_age_hours": max_age_hours,
            "stale": True,
            "reason": "missing",
        }

    modified = datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=timezone.utc,
    )

    age_hours = (
        utc_now() - modified
    ).total_seconds() / 3600.0

    return {
        "path": str(path),
        "exists": True,
        "modified_at": modified.isoformat(),
        "age_hours": round(age_hours, 4),
        "max_age_hours": max_age_hours,
        "stale": age_hours > max_age_hours,
        "reason": (
            "source_stale"
            if age_hours > max_age_hours
            else "source_fresh"
        ),
    }


def derive_coherence_status(
    master_coherence: dict[str, Any],
) -> str:
    status = str(
        master_coherence.get("status")
        or master_coherence.get("summary", {}).get("status")
        or "unknown"
    ).lower()

    errors = master_coherence.get("errors") or []
    warnings = master_coherence.get("warnings") or []

    if status in {"ok", "pass", "passed"} and not errors:
        return "PASS_WITH_WARNINGS" if warnings else "PASS"

    return "FAIL"


def derive_supervision_status(
    supervision_gate: dict[str, Any],
    institutional_supervision: dict[str, Any],
    global_orchestration: dict[str, Any],
) -> str:
    candidates = [
        supervision_gate.get("status"),
        supervision_gate.get("decision"),
        supervision_gate.get("gate_status"),
        institutional_supervision.get("status"),
        institutional_supervision.get("decision"),
        global_orchestration.get("status"),
    ]

    normalized = {
        str(value).upper()
        for value in candidates
        if value is not None
    }

    blocking_tokens = {
        "BLOCK",
        "BLOCKED",
        "BLOCKING",
        "FAIL",
        "FAILED",
        "KO",
        "REJECTED",
    }

    if normalized & blocking_tokens:
        return "BLOCKED"

    pass_tokens = {
        "OK",
        "PASS",
        "PASSED",
        "APPROVED",
        "READY",
    }

    if normalized & pass_tokens:
        return "PASS"

    return "UNKNOWN"


def derive_execution_posture(
    governance: dict[str, Any],
    rebalance_plan: dict[str, Any],
    supervision_status: str,
) -> tuple[str, bool, list[str]]:
    reasons: list[str] = []

    hard_block = bool(governance.get("hard_block"))
    soft_veto = bool(governance.get("soft_veto"))

    action_policy = str(
        governance.get("action_policy") or "UNKNOWN"
    ).upper()

    rebalance_execution_allowed = bool(
        rebalance_plan.get("execution_allowed")
    )

    caps = governance.get("caps") or {}
    max_orders = int(
        safe_float(caps.get("max_orders_per_run"), 0.0)
    )

    if hard_block:
        reasons.append("governance_hard_block_active")

    if soft_veto:
        reasons.append("governance_soft_veto_active")

    if action_policy == "SIMULATED_ONLY":
        reasons.append("governance_action_policy_simulated_only")

    if action_policy in {
        "EXIT_ONLY",
        "OBSERVATION_ONLY",
        "SHADOW_ONLY",
    }:
        reasons.append(
            f"governance_action_policy_{action_policy.lower()}"
        )

    if max_orders <= 0:
        reasons.append("governance_max_orders_per_run_zero")

    if not rebalance_execution_allowed:
        reasons.append("rebalance_execution_not_allowed")

    if supervision_status == "BLOCKED":
        reasons.append("supervision_gate_blocked")

    real_execution_allowed = (
        not hard_block
        and not soft_veto
        and action_policy in {"NORMAL", "LIVE", "PRODUCTION"}
        and rebalance_execution_allowed
        and max_orders > 0
        and supervision_status != "BLOCKED"
    )

    if real_execution_allowed:
        return "REAL_EXECUTION_ALLOWED", True, reasons

    if hard_block or supervision_status == "BLOCKED":
        return "BLOCKED", False, reasons

    if action_policy == "SIMULATED_ONLY":
        return "SIMULATED_ONLY", False, reasons

    if action_policy == "EXIT_ONLY":
        return "EXIT_ONLY", False, reasons

    return "NO_REAL_EXECUTION", False, reasons


def derive_governance_posture(
    governance: dict[str, Any],
    execution_posture: str,
) -> str:
    if bool(governance.get("hard_block")):
        return "BLOCKED"

    if bool(governance.get("soft_veto")):
        return "SOFT_VETO"

    if execution_posture == "SIMULATED_ONLY":
        return "PASS_WITH_EXECUTION_RESTRICTION"

    flag = str(
        governance.get("flag")
        or governance.get("mode")
        or "unknown"
    ).lower()

    if flag in {"ok", "pass", "passed"}:
        return "PASS"

    return "WATCH"


def derive_risk_posture(
    governance: dict[str, Any],
) -> tuple[str, float, list[str]]:
    inputs = governance.get("inputs") or {}
    risk_engine = inputs.get("risk_engine") or {}
    risk_limits = inputs.get("risk_limits") or {}

    risk_score = normalize_confidence(
        risk_engine.get("risk_score")
        or risk_engine.get("score")
    )

    risk_flag = str(
        risk_engine.get("global_flag")
        or risk_engine.get("flag")
        or "unknown"
    ).lower()

    correlation = governance.get("correlation") or {}
    correlation_gate = (
        governance.get("correlation_gate_state")
        or correlation.get("gate")
        or {}
    )

    correlation_active = bool(
        correlation_gate.get("active")
    )

    kill_switch = (
        risk_limits.get("kill_switch")
        or inputs.get("kill_switch")
        or {}
    )

    reasons: list[str] = []

    if correlation_active:
        reasons.append("correlation_gate_active")

    if bool(kill_switch.get("hard_block")):
        reasons.append("kill_switch_hard_block")

    if bool(kill_switch.get("soft_block")):
        reasons.append("kill_switch_soft_block")

    if bool(governance.get("hard_block")):
        return "BLOCKED", risk_score, reasons

    if bool(kill_switch.get("hard_block")):
        return "BLOCKED", risk_score, reasons

    if risk_flag in {"risk_off", "high_risk", "critical"}:
        return "RISK_OFF", risk_score, reasons

    if correlation_active:
        return (
            "CONTROLLED_RISK_ON_WITH_CORRELATION_WATCH",
            risk_score,
            reasons,
        )

    if risk_flag == "risk_on":
        return "CONTROLLED_RISK_ON", risk_score, reasons

    return "NEUTRAL_WATCH", risk_score, reasons


def build_brick_decisions(
    portfolio_target: dict[str, Any],
    portfolio_state: dict[str, Any],
    rebalance_plan: dict[str, Any],
    execution_posture: str,
) -> dict[str, dict[str, Any]]:
    target_weights = (
        portfolio_target.get("final_brick_weights") or {}
    )

    state_bricks = portfolio_state.get("bricks") or {}

    rebalance_actions = {
        item.get("brick"): item
        for item in rebalance_plan.get("actions", [])
        if isinstance(item, dict) and item.get("brick")
    }

    result: dict[str, dict[str, Any]] = {}

    for brick, target_weight in target_weights.items():
        state = state_bricks.get(brick) or {}
        action = rebalance_actions.get(brick) or {}

        status = str(action.get("status") or "unknown").lower()
        delta_amount = safe_float(
            action.get("proposed_delta_amount_eur"),
            0.0,
        )
        raw_delta_amount = safe_float(
            action.get("delta_amount_eur"),
            0.0,
        )

        if status == "proposed":
            if delta_amount > 0:
                recommendation = "INCREASE"
            elif delta_amount < 0:
                recommendation = "DECREASE"
            elif raw_delta_amount > 0:
                recommendation = "INCREASE"
            elif raw_delta_amount < 0:
                recommendation = "DECREASE"
            else:
                recommendation = "HOLD"
        elif status in {"deferred", "within_band", "hold"}:
            recommendation = "HOLD"
        else:
            recommendation = "OBSERVE"

        if recommendation in {"INCREASE", "DECREASE"}:
            if execution_posture == "SIMULATED_ONLY":
                executive_action = (
                    f"SIMULATE_{recommendation}"
                )
            elif execution_posture == "REAL_EXECUTION_ALLOWED":
                executive_action = recommendation
            else:
                executive_action = (
                    f"PROPOSE_{recommendation}_NO_EXECUTION"
                )
        else:
            executive_action = recommendation

        result[brick] = {
            "status": state.get("status"),
            "target_weight": round(
                safe_float(target_weight),
                6,
            ),
            "current_weight_estimate": round(
                safe_float(
                    state.get("current_weight_estimate"),
                    state.get("current", 0.0),
                ),
                6,
            ),
            "confidence": normalize_confidence(
                state.get(
                    "confidence",
                    (
                        portfolio_target
                        .get("brick_confidence", {})
                        .get(brick)
                    ),
                )
            ),
            "rebalance_status": action.get("status"),
            "delta_weight": safe_float(
                action.get("delta_weight"),
                0.0,
            ),
            "proposed_delta_weight": safe_float(
                action.get("proposed_delta_weight"),
                0.0,
            ),
            "proposed_delta_amount_eur": safe_float(
                action.get("proposed_delta_amount_eur"),
                0.0,
            ),
            "manual_approval_required": bool(
                action.get(
                    "manual_approval_required",
                    True,
                )
            ),
            "execution_allowed": bool(
                action.get("execution_allowed")
            ),
            "recommendation": recommendation,
            "executive_action": executive_action,
            "reason": action.get("reason"),
        }

    return result


def compute_decision_confidence(
    portfolio_target: dict[str, Any],
    governance: dict[str, Any],
    risk_score: float,
    coherence_status: str,
    supervision_status: str,
    source_freshness: dict[str, dict[str, Any]],
) -> tuple[float, list[dict[str, Any]]]:
    brick_confidences = [
        normalize_confidence(value)
        for value in (
            portfolio_target.get("brick_confidence") or {}
        ).values()
    ]

    avg_brick_confidence = (
        mean(brick_confidences)
        if brick_confidences
        else 0.0
    )

    governance_confidence = normalize_confidence(
        governance.get("score")
    )

    coherence_confidence = (
        1.0
        if coherence_status == "PASS"
        else 0.85
        if coherence_status == "PASS_WITH_WARNINGS"
        else 0.0
    )

    supervision_confidence = (
        1.0
        if supervision_status == "PASS"
        else 0.5
        if supervision_status == "UNKNOWN"
        else 0.0
    )

    critical_sources = [
        "portfolio_target",
        "portfolio_state",
        "rebalance_plan",
        "governance",
    ]

    fresh_count = sum(
        1
        for name in critical_sources
        if not source_freshness[name]["stale"]
    )

    freshness_confidence = (
        fresh_count / len(critical_sources)
    )

    drivers = [
        {
            "driver": "Portfolio Brick Confidence",
            "weight": 0.30,
            "value": round(avg_brick_confidence, 4),
        },
        {
            "driver": "Governance Confidence",
            "weight": 0.20,
            "value": round(governance_confidence, 4),
        },
        {
            "driver": "Risk Confidence",
            "weight": 0.20,
            "value": round(risk_score, 4),
        },
        {
            "driver": "Master Coherence",
            "weight": 0.10,
            "value": round(coherence_confidence, 4),
        },
        {
            "driver": "Supervision",
            "weight": 0.10,
            "value": round(supervision_confidence, 4),
        },
        {
            "driver": "Critical Source Freshness",
            "weight": 0.10,
            "value": round(freshness_confidence, 4),
        },
    ]

    score = sum(
        item["weight"] * item["value"]
        for item in drivers
    )

    return round(clamp(score), 4), drivers


def derive_primary_action(
    brick_decisions: dict[str, dict[str, Any]],
) -> tuple[str, str | None, float]:
    actionable: list[tuple[str, dict[str, Any]]] = []

    for brick, decision in brick_decisions.items():
        if decision.get("recommendation") in {
            "INCREASE",
            "DECREASE",
        }:
            actionable.append((brick, decision))

    if not actionable:
        return "HOLD_PORTFOLIO", None, 0.0

    actionable.sort(
        key=lambda row: abs(
            safe_float(
                row[1].get("proposed_delta_amount_eur"),
                0.0,
            )
            or safe_float(
                row[1].get("delta_weight"),
                0.0,
            )
        ),
        reverse=True,
    )

    brick, decision = actionable[0]

    return (
        str(decision.get("executive_action")),
        brick,
        safe_float(
            decision.get("proposed_delta_amount_eur"),
            0.0,
        ),
    )


def main() -> int:
    generated_at = iso_now()

    portfolio_target = read_json(
        PATHS["portfolio_target"],
        {},
    )
    portfolio_state = read_json(
        PATHS["portfolio_state"],
        {},
    )
    rebalance_plan = read_json(
        PATHS["rebalance_plan"],
        {},
    )
    allocation_policy = read_json(
        PATHS["allocation_policy"],
        {},
    )
    governance = read_json(
        PATHS["governance"],
        {},
    )
    master_coherence = read_json(
        PATHS["master_coherence"],
        {},
    )
    global_orchestration = read_json(
        PATHS["global_orchestration"],
        {},
    )
    supervision_gate = read_json(
        PATHS["supervision_gate"],
        {},
    )
    institutional_supervision = read_json(
        PATHS["institutional_supervision"],
        {},
    )
    operational_confidence = read_json(
        PATHS["operational_confidence"],
        {},
    )
    execution_confidence = read_json(
        PATHS["execution_confidence"],
        {},
    )

    required_inputs = {
        "portfolio_target": portfolio_target,
        "portfolio_state": portfolio_state,
        "rebalance_plan": rebalance_plan,
        "allocation_policy": allocation_policy,
        "governance": governance,
    }

    missing_required_inputs = [
        name
        for name, payload in required_inputs.items()
        if not payload
    ]

    source_freshness = {
        name: file_freshness(
            path,
            24.0 if name != "allocation_policy" else 24 * 365,
        )
        for name, path in PATHS.items()
    }

    stale_critical_inputs = [
        name
        for name in required_inputs
        if source_freshness[name]["stale"]
    ]

    coherence_status = derive_coherence_status(
        master_coherence
    )

    supervision_status = derive_supervision_status(
        supervision_gate,
        institutional_supervision,
        global_orchestration,
    )

    execution_posture, real_execution_allowed, blocking_reasons = (
        derive_execution_posture(
            governance,
            rebalance_plan,
            supervision_status,
        )
    )

    governance_posture = derive_governance_posture(
        governance,
        execution_posture,
    )

    risk_posture, risk_score, risk_reasons = (
        derive_risk_posture(governance)
    )

    blocking_reasons.extend(risk_reasons)

    if missing_required_inputs:
        blocking_reasons.extend(
            f"missing_required_input_{name}"
            for name in missing_required_inputs
        )

    if stale_critical_inputs:
        blocking_reasons.extend(
            f"stale_critical_input_{name}"
            for name in stale_critical_inputs
        )

    blocking_reasons = list(
        dict.fromkeys(blocking_reasons)
    )

    brick_decisions = build_brick_decisions(
        portfolio_target,
        portfolio_state,
        rebalance_plan,
        execution_posture,
    )

    primary_action, primary_brick, primary_amount = (
        derive_primary_action(brick_decisions)
    )

    decision_confidence, confidence_drivers = (
        compute_decision_confidence(
            portfolio_target,
            governance,
            risk_score,
            coherence_status,
            supervision_status,
            source_freshness,
        )
    )

    portfolio_regime = str(
        portfolio_target.get("portfolio_regime")
        or portfolio_state.get("portfolio_regime")
        or allocation_policy.get("portfolio_regime")
        or "unknown"
    )

    proposed_actions = [
        item
        for item in brick_decisions.values()
        if item.get("recommendation") in {
            "INCREASE",
            "DECREASE",
        }
    ]

    if missing_required_inputs or stale_critical_inputs:
        portfolio_posture = "DATA_QUALITY_BLOCK"
        executive_decision = "OBSERVE"
    elif governance_posture == "BLOCKED":
        portfolio_posture = "RISK_CONTROL"
        executive_decision = "BLOCK"
    elif proposed_actions:
        portfolio_posture = (
            "RISK_ON_SELECTIVE"
            if portfolio_regime == "risk_on"
            else "SELECTIVE_REBALANCE"
        )
        executive_decision = primary_action
    else:
        portfolio_posture = (
            "RISK_ON_HOLD"
            if portfolio_regime == "risk_on"
            else "HOLD"
        )
        executive_decision = "HOLD_PORTFOLIO"

    manual_approval_required = any(
        bool(item.get("manual_approval_required"))
        for item in brick_decisions.values()
        if item.get("recommendation") in {
            "INCREASE",
            "DECREASE",
        }
    )

    waterfall = [
        {
            "step": "Portfolio Target",
            "status": (
                "PASS"
                if portfolio_target
                and not source_freshness[
                    "portfolio_target"
                ]["stale"]
                else "FAIL"
            ),
            "score": round(
                sum(
                    safe_float(value)
                    for value in (
                        portfolio_target.get(
                            "final_brick_weights"
                        )
                        or {}
                    ).values()
                ),
                6,
            ),
        },
        {
            "step": "Portfolio State",
            "status": (
                "PASS"
                if portfolio_state
                and not source_freshness[
                    "portfolio_state"
                ]["stale"]
                else "FAIL"
            ),
            "score": safe_float(
                portfolio_state.get(
                    "live_exposure_ratio"
                ),
                0.0,
            ),
        },
        {
            "step": "Rebalance",
            "status": (
                "PROPOSED"
                if proposed_actions
                else "HOLD"
            ),
            "score": len(proposed_actions),
        },
        {
            "step": "Master Coherence",
            "status": coherence_status,
            "score": (
                1.0
                if coherence_status == "PASS"
                else 0.0
            ),
        },
        {
            "step": "Risk",
            "status": risk_posture,
            "score": round(risk_score, 4),
        },
        {
            "step": "Governance",
            "status": governance_posture,
            "score": normalize_confidence(
                governance.get("score")
            ),
        },
        {
            "step": "Supervision",
            "status": supervision_status,
            "score": (
                1.0
                if supervision_status == "PASS"
                else 0.0
            ),
        },
        {
            "step": "Execution",
            "status": execution_posture,
            "score": 1.0 if real_execution_allowed else 0.0,
        },
        {
            "step": "Executive Decision",
            "status": executive_decision,
            "score": decision_confidence,
        },
    ]

    action_policy = str(
        governance.get("action_policy") or "UNKNOWN"
    ).upper()

    payload = {
        "status": (
            "blocked"
            if missing_required_inputs
            or stale_critical_inputs
            else "ok"
        ),
        "generated_at": generated_at,
        "engine": "executive_decision_engine_v2",
        "engine_version": "2.0.0",
        "decision": executive_decision,
        "recommended_action": executive_decision,
        "recommended_symbol": None,
        "recommended_brick": primary_brick,
        "recommended_amount_eur": round(
            primary_amount,
            2,
        ),
        "decision_score": round(
            decision_confidence * 100,
            2,
        ),
        "confidence": decision_confidence,
        "confidence_pct": round(
            decision_confidence * 100,
            2,
        ),
        "decision_confidence": decision_confidence,
        "decision_confidence_pct": round(
            decision_confidence * 100,
            2,
        ),
        "portfolio_regime": portfolio_regime,
        "portfolio_posture": portfolio_posture,
        "capital_posture": (
            "DEPLOY_SELECTIVELY"
            if proposed_actions
            else "MAINTAIN"
        ),
        "execution_posture": execution_posture,
        "governance_posture": governance_posture,
        "risk_posture": risk_posture,
        "supervision_status": supervision_status,
        "coherence_status": coherence_status,
        "action_policy": action_policy,
        "execution_allowed": real_execution_allowed,
        "real_execution_authorized": real_execution_allowed,
        "simulation_authorized": (
            action_policy == "SIMULATED_ONLY"
            and not bool(governance.get("hard_block"))
        ),
        "manual_approval_required": (
            manual_approval_required
        ),
        "blocking_reasons": blocking_reasons,
        "missing_required_inputs": missing_required_inputs,
        "stale_critical_inputs": stale_critical_inputs,
        "governed_brick_decisions": brick_decisions,
        "portfolio_summary": {
            "total_value_eur": safe_float(
                portfolio_state.get(
                    "total_value_eur"
                ),
                0.0,
            ),
            "capital_engaged_eur": safe_float(
                portfolio_state.get(
                    "capital_engaged_eur"
                ),
                0.0,
            ),
            "cash_available_eur": safe_float(
                portfolio_state.get(
                    "cash_available_eur"
                ),
                0.0,
            ),
            "live_exposure_ratio": safe_float(
                portfolio_state.get(
                    "live_exposure_ratio"
                ),
                0.0,
            ),
            "cash_buffer_target": safe_float(
                portfolio_target.get(
                    "cash_buffer"
                ),
                0.0,
            ),
            "actions_total": int(
                safe_float(
                    rebalance_plan.get(
                        "summary",
                        {},
                    ).get("actions_total"),
                    0.0,
                )
            ),
            "actions_proposed": int(
                safe_float(
                    rebalance_plan.get(
                        "summary",
                        {},
                    ).get("actions_proposed"),
                    0.0,
                )
            ),
        },
        "risk_summary": {
            "risk_score": round(risk_score, 4),
            "governance_score": normalize_confidence(
                governance.get("score")
            ),
            "hard_block": bool(
                governance.get("hard_block")
            ),
            "soft_veto": bool(
                governance.get("soft_veto")
            ),
            "correlation_gate_active": bool(
                (
                    governance.get(
                        "correlation_gate_state"
                    )
                    or governance.get(
                        "correlation",
                        {},
                    ).get("gate")
                    or {}
                ).get("active")
            ),
        },
        "operational_confidence": (
            operational_confidence
        ),
        "execution_confidence": (
            execution_confidence
        ),
        "waterfall": waterfall,
        "drivers": confidence_drivers,
        "rejections": [],
        "source_freshness": source_freshness,
        "source_paths": {
            key: str(value)
            for key, value in PATHS.items()
        },
        "narrative": (
            f"Executive Decision V2: {executive_decision}. "
            f"Portfolio posture is {portfolio_posture}; "
            f"execution posture is {execution_posture}; "
            f"governance posture is {governance_posture}; "
            f"risk posture is {risk_posture}. "
            f"Primary governed action targets "
            f"{primary_brick or 'no brick'}"
            f"{f' for EUR {primary_amount:.2f}' if primary_brick else ''}. "
            f"Real execution is "
            f"{'authorized' if real_execution_allowed else 'not authorized'}."
        ),
    }

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    previous_history: list[dict[str, Any]] = []

    try:
        for path in sorted(
            HISTORY_DIR.glob(
                "executive_decision_*.json"
            ),
            reverse=True,
        )[:19]:
            history_item = read_json(path, {})

            if history_item:
                previous_history.append(
                    {
                        "generated_at": history_item.get(
                            "generated_at"
                        ),
                        "engine": history_item.get(
                            "engine"
                        ),
                        "decision": history_item.get(
                            "decision"
                        ),
                        "recommended_brick": (
                            history_item.get(
                                "recommended_brick"
                            )
                        ),
                        "decision_confidence": (
                            history_item.get(
                                "decision_confidence",
                                history_item.get(
                                    "confidence"
                                ),
                            )
                        ),
                        "execution_posture": (
                            history_item.get(
                                "execution_posture"
                            )
                        ),
                        "risk_posture": (
                            history_item.get(
                                "risk_posture"
                            )
                        ),
                    }
                )
    except Exception:
        previous_history = []

    current_compact = {
        "generated_at": generated_at,
        "engine": payload["engine"],
        "decision": executive_decision,
        "recommended_brick": primary_brick,
        "recommended_amount_eur": round(
            primary_amount,
            2,
        ),
        "decision_confidence": (
            decision_confidence
        ),
        "execution_posture": execution_posture,
        "governance_posture": governance_posture,
        "risk_posture": risk_posture,
    }

    payload["history"] = (
        [current_compact] + previous_history
    )

    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    CURRENT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    stamp = utc_now().strftime(
        "%Y%m%dT%H%M%SZ"
    )

    history_payload = dict(payload)
    history_payload.pop("history", None)

    history_path = (
        HISTORY_DIR
        / f"executive_decision_{stamp}.json"
    )

    history_path.write_text(
        json.dumps(
            history_payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": payload["status"],
                "engine": payload["engine"],
                "decision": payload["decision"],
                "recommended_brick": (
                    payload["recommended_brick"]
                ),
                "recommended_amount_eur": (
                    payload["recommended_amount_eur"]
                ),
                "decision_confidence": (
                    payload["decision_confidence"]
                ),
                "decision_confidence_pct": (
                    payload[
                        "decision_confidence_pct"
                    ]
                ),
                "portfolio_posture": (
                    payload["portfolio_posture"]
                ),
                "execution_posture": (
                    payload["execution_posture"]
                ),
                "governance_posture": (
                    payload["governance_posture"]
                ),
                "risk_posture": (
                    payload["risk_posture"]
                ),
                "action_policy": (
                    payload["action_policy"]
                ),
                "execution_allowed": (
                    payload["execution_allowed"]
                ),
                "manual_approval_required": (
                    payload[
                        "manual_approval_required"
                    ]
                ),
                "blocking_reasons": (
                    payload["blocking_reasons"]
                ),
                "output": str(CURRENT_PATH),
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
