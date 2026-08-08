#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _as_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _veto(veto_type: str, code: str, message: str) -> Dict[str, str]:
    return {"type": veto_type, "code": code, "message": message}

def enforce_governance_on_plan(
    governance: Dict[str, Any],
    execution_plan: Dict[str, Any],
    *,
    estimated_notional_usd: Optional[float] = None,
    correlation_gate_state: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[Dict[str, str]], Dict[str, Any]]:
    """
    Returns (allowed, vetos, plan_out).
    - hard_block => allowed False
    - soft_veto => allowed True but should reduce/skip depending on upstream policy
    Here, we keep allowed=True for soft_veto and attach vetos in plan.validations.
    """
    vetos: List[Dict[str, str]] = []
    plan = dict(execution_plan)  # shallow copy

    mode = str(governance.get("mode", "PREPROD")).upper()
    policy = str(governance.get("action_policy", "SIMULATED_ONLY")).upper()
    caps = governance.get("caps", {}) or {}
    flags = governance.get("feature_flags", {}) or {}

    # --- Global policy: PREPROD => allow safe paper modes, forbid LIVE
    allowed_preprod_policies = {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "EXIT_ONLY"}
    if mode == "PREPROD" and policy not in allowed_preprod_policies:
        vetos.append(_veto("hard_block", "PREPROD_POLICY", "PREPROD must run in a safe simulated mode"))
        return (False, vetos, _attach(plan, vetos, is_simulated=True))

    is_simulated = (policy in {"SIMULATED_ONLY", "SIMULATED_EXECUTION", "EXIT_ONLY"})

    # --- Correlation gate: per decision (per our NSC decision: correlation_gate_state.active => SOFT veto)
    if correlation_gate_state and bool(correlation_gate_state.get("active")):
        vetos.append(_veto("soft_veto", "CORRELATION_GATE_ACTIVE", "Correlation gate active (soft veto)"))

    # --- Basic required fields sanity
    for req in ["symbol", "side", "qty", "order_type", "time_in_force", "derived_from", "ts"]:
        if req not in plan:
            vetos.append(_veto("hard_block", "PLAN_MISSING_FIELD", f"execution_plan missing required field: {req}"))
            return (False, vetos, _attach(plan, vetos, is_simulated=is_simulated))

    qty = _as_float(plan.get("qty"), 0.0)
    if qty <= 0:
        vetos.append(_veto("hard_block", "INVALID_QTY", "qty must be > 0"))
        return (False, vetos, _attach(plan, vetos, is_simulated=is_simulated))

    # --- Notional caps
    max_order_notional = _as_float(caps.get("max_order_notional_usd"), 0.0)
    max_total_notional = _as_float(caps.get("max_notional_usd"), 0.0)

    # Estimate notional if not provided
    notional = _as_float(estimated_notional_usd, 0.0)
    if notional <= 0:
        # Try infer from limit_price if present
        px = _as_float(plan.get("limit_price"), 0.0)
        if px > 0:
            notional = px * qty

    if max_order_notional > 0 and notional > max_order_notional:
        vetos.append(_veto("hard_block", "CAP_MAX_ORDER_NOTIONAL", f"Order notional {notional:.2f} > cap {max_order_notional:.2f}"))
        return (False, vetos, _attach(plan, vetos, is_simulated=is_simulated))

    # Note: max_total_notional is usually checked at orchestrator level (aggregate).
    # Here we still attach it as a validation hint if provided.
    if max_total_notional > 0 and notional > max_total_notional:
        vetos.append(_veto("hard_block", "CAP_MAX_TOTAL_NOTIONAL", f"Notional {notional:.2f} > global cap {max_total_notional:.2f}"))
        return (False, vetos, _attach(plan, vetos, is_simulated=is_simulated))

    # --- Max orders is also orchestrator-level, but we keep hint
    max_orders = _as_int(caps.get("max_orders"), 0)

    # --- Idempotency enforcement
    if bool(flags.get("enforce_idempotency", True)):
        validations = plan.get("validations") or {}
        idem_key = validations.get("idempotency_key")
        if not idem_key:
            vetos.append(_veto("hard_block", "MISSING_IDEMPOTENCY_KEY", "idempotency_key required by governance"))
            return (False, vetos, _attach(plan, vetos, is_simulated=is_simulated))

    # Attach validations
    plan_out = _attach(
        plan,
        vetos,
        is_simulated=is_simulated,
        caps_ok=(len([v for v in vetos if v["type"] == "hard_block"]) == 0),
        max_orders=max_orders,
        estimated_notional_usd=notional if notional > 0 else None,
    )

    hard_blocks = [v for v in vetos if v["type"] == "hard_block"]
    allowed = (len(hard_blocks) == 0)
    return (allowed, vetos, plan_out)

def _attach(plan: Dict[str, Any], vetos: List[Dict[str, str]], **extra: Any) -> Dict[str, Any]:
    out = dict(plan)
    validations = dict(out.get("validations") or {})
    validations["vetos"] = vetos
    for k, v in extra.items():
        if v is not None:
            validations[k] = v
    out["validations"] = validations
    return out
