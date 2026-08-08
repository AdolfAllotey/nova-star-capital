from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


APP_ROOT = Path("/opt/nsc/app")
DATA_ROOT = APP_ROOT / "src/v2/data"

FILES = {
    "portfolio_target": DATA_ROOT / "portfolio/portfolio_target.json",
    "portfolio_state": DATA_ROOT / "portfolio/state/portfolio_state.json",
    "allocation_policy": DATA_ROOT / "portfolio/policy/allocation_policy.json",
    "aggregator_explainability": DATA_ROOT / "portfolio/aggregator_explainability.json",
    "aggregator_audit": DATA_ROOT / "portfolio/aggregator_audit.json",
    "rebalance_plan": DATA_ROOT / "portfolio/rebalance/rebalance_plan.json",
}

OUTPUT = DATA_ROOT / "orchestration/global_orchestration_audit.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {"__missing__": True, "__path__": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": str(exc), "__path__": str(path)}


def get_regime(doc: dict) -> str:
    return str(
        doc.get("portfolio_regime")
        or doc.get("final_decision", {}).get("regime")
        or doc.get("regime")
        or "UNKNOWN"
    )


def get_ts(doc: dict) -> str | None:
    return doc.get("timestamp") or doc.get("ts")


def main() -> None:
    docs = {name: read_json(path) for name, path in FILES.items()}

    checks = []
    warnings = []
    hard_failures = []

    for name, doc in docs.items():
        if doc.get("__missing__"):
            hard_failures.append(f"{name} missing: {doc.get('__path__')}")
        elif doc.get("__error__"):
            hard_failures.append(f"{name} unreadable: {doc.get('__error__')}")
        else:
            checks.append(f"{name} loaded")

    target_regime = get_regime(docs["portfolio_target"])
    state_regime = get_regime(docs["portfolio_state"])
    explain_regime = get_regime(docs["aggregator_explainability"])
    audit_regime = get_regime(docs["aggregator_audit"])
    rebalance_regime = get_regime(docs["rebalance_plan"])

    regime_map = {
        "portfolio_target": target_regime,
        "portfolio_state": state_regime,
        "aggregator_explainability": explain_regime,
        "aggregator_audit": audit_regime,
        "rebalance_plan": rebalance_regime,
    }

    for name, regime in regime_map.items():
        if regime != "UNKNOWN" and target_regime != "UNKNOWN" and regime != target_regime:
            warnings.append(f"regime mismatch: {name}={regime} vs portfolio_target={target_regime}")

    target = docs["portfolio_target"]
    final_weights = target.get("final_brick_weights", {}) if isinstance(target, dict) else {}
    cash_buffer = float(target.get("cash_buffer", 0) or 0)
    total_final_weight = sum(float(v or 0) for v in final_weights.values())
    sum_with_cash = round(total_final_weight + cash_buffer, 6)

    if abs(sum_with_cash - 1.0) > 0.01:
        warnings.append(f"allocation sum_with_cash={sum_with_cash}, expected around 1.0")

    output = {
        "status": "ok" if not hard_failures else "error",
        "mode": "PREPROD_SHADOW_AUDIT_ONLY",
        "engine": "nsc_global_orchestrator_preprod_v0",
        "timestamp": now_iso(),
        "execution_allowed": False,
        "writes_execution_plan": False,
        "regime_map": regime_map,
        "allocation_summary": {
            "total_final_weight": total_final_weight,
            "cash_buffer": cash_buffer,
            "sum_with_cash": sum_with_cash,
            "final_brick_weights": final_weights,
        },
        "timestamps": {name: get_ts(doc) for name, doc in docs.items()},
        "checks": checks,
        "warnings": warnings,
        "hard_failures": hard_failures,
        "recommendation": "Do not execute automatically. Use this report to align stale artefacts before connecting orchestration.",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
