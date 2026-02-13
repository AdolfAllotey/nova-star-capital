#!/usr/bin/env python3
from __future__ import annotations


def ensure_preprod_artifacts() -> None:
    """
    Ensure required state/jsonl artifacts exist for preprod_check, even when no orders are produced.
    Best-effort: never raise, never blocks the run.
    """
    cmds = [
        ["python", "src/v2/equities_offensive/broker/simulated_broker.py"],
        ["python", "src/v2/equities_offensive/execution/position_tracker.py"],
        ["python", "src/v2/equities_offensive/ui/ui_bundle_builder.py"],
    ]
    for cmd in cmds:
        try:
            subprocess.run(cmd, check=False)
        except Exception:
            # fail-safe: do not block pipeline
            pass

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.governance.governance_loader import load_governance
from src.v2.governance.governance_enforcer import enforce_governance_on_plan
from src.v2.equities_offensive.market.price_feed import get_last_price
from src.v2.equities_offensive.position_sizer import size_qty_from_budget

# -------- utils

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

# -------- placeholder engines (V0)
# Ici on ne fait PAS encore de stratégie : juste une pipeline propre.

def build_stub_signal(inputs: Dict[str, Any]) -> Dict[str, Any]:
    # Stub: exemple NVDA long, score piloté par regime
    regime = ((inputs.get("market_regime") or {}).get("regime")) or "neutral"
    base = 60.0 if regime == "risk_on" else (45.0 if regime == "neutral" else 25.0)

    return {
        "engine": "stub_engine_v0",
        "symbol": "NVDA",
        "direction": "long",
        "score": clamp(base, 0, 100),
        "timeframe": "D1",
        "ts": utc_now_iso(),
        "features": {
            "market_regime": regime
        },
        "reasons": [f"stub signal (regime={regime})"],
        "meta": {
            "source": "equities_offensive",
            "version": "0.1"
        }
    }

def vote_signal(signal: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    # Stub voting: pass-through with simple threshold
    min_score = 50.0
    ok = float(signal.get("score", 0)) >= min_score

    out = dict(signal)
    out["meta"] = dict(out.get("meta") or {})
    out["meta"]["voting"] = {"min_score": min_score, "passed": ok}
    return out

def risk_decide(voted: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    budget = float(inputs.get("budget_trading") or 0.0)
    passed = bool(((voted.get("meta") or {}).get("voting") or {}).get("passed"))

    allowed = passed and budget > 0
    reason = "ok" if allowed else ("budget_zero" if budget <= 0 else "vote_failed")

    # sizing ultra simple V0 : 5% du budget (capé)
    size_usd = 0.0
    if allowed:
        size_usd = min(budget * 0.05, 25000.0)

    return {
        "symbol": voted.get("symbol"),
        "allowed": bool(allowed),
        "ts": utc_now_iso(),
        "reason": reason,
        "size_usd": round(float(size_usd), 2),
        "risk_mode": ((inputs.get("market_regime") or {}).get("regime") or "neutral"),
        "caps": inputs.get("caps", {}) or {},
        "vetos": [],
        "meta": {"source": "equities_offensive", "version": "0.1"}
    }

def build_execution_plan(risk: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    if not risk.get("allowed"):
        return {
            "ts": utc_now_iso(),
            "derived_from": "risk_decision",
            "skip": True,
            "reason": risk.get("reason", "not_allowed")
        }

    symbol = str(risk["symbol"])
    size_usd = float(risk.get("size_usd") or 0.0)
    caps = inputs.get("caps", {}) or {}

    # Price feed (minimal)
    px = get_last_price(symbol, prices_path="data/market/prices.json")
    if px is None or px <= 0:
        return {
            "ts": utc_now_iso(),
            "derived_from": "risk_decision",
            "skip": True,
            "reason": "missing_price",
            "symbol": symbol
        }

    sizing = size_qty_from_budget(size_usd=size_usd, price=float(px), caps=caps)
    if sizing.qty <= 0:
        return {
            "ts": utc_now_iso(),
            "derived_from": "risk_decision",
            "skip": True,
            "reason": "sizing_qty_zero",
            "symbol": symbol,
            "price": float(px),
            "sizing_warnings": sizing.warnings
        }

    plan = {
        "symbol": symbol,
        "side": "buy",
        "qty": sizing.qty,
        "order_type": "market",
        "time_in_force": "DAY",
        "ts": utc_now_iso(),
        "derived_from": "risk_decision",
        "limit_price": None,
        "validations": {
            "idempotency_key": f"equ_off|{symbol}|buy|{sizing.qty}|{round(float(px), 4)}|{risk.get('ts')}"
        },
        "meta": {
            "source": "equities_offensive",
            "version": "0.2",
            "price": float(px),
            "notional_estimate": round(float(sizing.notional), 2),
            "sizing_warnings": sizing.warnings
        }
    }
    return plan

# -------- contracts validation (optional if jsonschema present)

def validate_contract(schema_path: Path, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return True, ["jsonschema missing -> skipped validation"]

    schema = load_json(schema_path, default={}) or {}
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(data), key=lambda e: e.path)
    if not errors:
        return True, []
    msgs = []
    for err in errors[:30]:
        loc = ".".join([str(x) for x in err.path]) if err.path else "(root)"
        msgs.append(f"{loc}: {err.message}")
    return False, msgs

# -------- runner

def run(
    inputs_path: str = "data/equities_offensive/inputs.json",
    out_dir: str = "data/equities_offensive/out"
) -> Dict[str, Any]:
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    inputs = load_json(Path(inputs_path), default={}) or {}
    governance = load_governance()

    # 1) signal
    signal = build_stub_signal(inputs)
    save_json(outp / "signal.json", signal)

    # validate
    ok, msgs = validate_contract(Path("src/v2/contracts/schemas/signal.schema.json"), signal)
    save_json(outp / "signal.validation.json", {"ok": ok, "messages": msgs})

    # 2) voted signal
    voted = vote_signal(signal, inputs)
    save_json(outp / "voted_signal.json", voted)

    # 3) risk decision
    risk = risk_decide(voted, inputs)
    save_json(outp / "risk_decision.json", risk)

    ok_r, msgs_r = validate_contract(Path("src/v2/contracts/schemas/risk_decision.schema.json"), risk)
    save_json(outp / "risk_decision.validation.json", {"ok": ok_r, "messages": msgs_r})

    # 4) execution plan
    plan = build_execution_plan(risk, inputs)

    # If plan is a "skip" object, still output it as is
    if plan.get("skip"):
        save_json(outp / "execution_plan.json", plan)
        return {"ts": utc_now_iso(), "status": "skipped", "reason": plan.get("reason")}

    # enforce governance on plan
    allowed, vetos, plan_out = enforce_governance_on_plan(
        governance,
        plan,
        estimated_notional_usd=None,
        correlation_gate_state=None
    )
    save_json(outp / "execution_plan.json", plan_out)

    ok_p, msgs_p = validate_contract(Path("src/v2/contracts/schemas/execution_plan.schema.json"), plan_out)
    save_json(outp / "execution_plan.validation.json", {"ok": ok_p, "messages": msgs_p})

    # 5) execution (PREPROD simulated only -> no real broker call)
    status = "allowed" if allowed else "blocked"
    return {"ts": utc_now_iso(), "status": status, "vetos": vetos}

def main():
    import argparse
    ap = argparse.ArgumentParser(description="NSC Equities Offensive Runner (Skeleton V0)")
    ap.add_argument("--inputs", default="data/equities_offensive/inputs.json")
    ap.add_argument("--out", default="data/equities_offensive/out")
    args = ap.parse_args()

    res = run(inputs_path=args.inputs, out_dir=args.out)
    print(json.dumps(res, ensure_ascii=False, indent=2))


# ensure required artifacts for preprod
ensure_preprod_artifacts()

if __name__ == "__main__":
    main()

# --- FINALIZATION (always run, even if execution is skipped) ---
from src.v2.equities_offensive.finalize_equities_state import main as finalize_equities_state
finalize_equities_state()
