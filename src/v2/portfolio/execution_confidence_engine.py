from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path("/opt/nsc/data/preprod")
OUT = BASE / "portfolio/audit/execution_confidence.json"

SOURCES = {
    "execution_plan": BASE / "trading/execution_plan.json",
    "governance": BASE / "analysis/governance_engine_pro.json",
    "supervision": BASE / "portfolio/audit/institutional_supervision_summary.json",
    "global_audit": BASE / "portfolio/audit/global_orchestration_audit.json",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_orders(plan: Any) -> list:
    if isinstance(plan, dict):
        for key in ("orders", "execution_plan", "items"):
            if isinstance(plan.get(key), list):
                return plan.get(key)
    if isinstance(plan, list):
        return plan
    return []


def main() -> dict:
    execution_plan = load(SOURCES["execution_plan"], {})
    governance = load(SOURCES["governance"], {})
    supervision = load(SOURCES["supervision"], {})
    global_audit = load(SOURCES["global_audit"], {})

    orders = get_orders(execution_plan)

    action_policy = str(governance.get("action_policy") or "SIMULATED_ONLY").upper()
    hard_block = bool(governance.get("hard_block", False))
    allow_simulated = bool((supervision.get("gate") or {}).get("allow_simulated_execution", True))
    allow_real = bool((supervision.get("gate") or {}).get("allow_real_execution", False))

    checks = [
        ("execution_plan_present", bool(execution_plan), 0.20),
        ("orders_structured", isinstance(orders, list), 0.20),
        ("governance_not_hard_blocked", not hard_block, 0.20),
        ("simulated_execution_authorized", allow_simulated and action_policy == "SIMULATED_ONLY", 0.25),
        ("real_execution_disabled", not allow_real, 0.15),
    ]

    if global_audit.get("blocking") is True:
        checks.append(("global_audit_not_blocking", False, 0.25))
    else:
        checks.append(("global_audit_not_blocking", True, 0.25))

    total = sum(weight for _, _, weight in checks)
    score = sum(weight for _, passed, weight in checks if passed)
    confidence = round(score / total, 4) if total else 0.0

    result = {
        "status": "ok",
        "engine": "execution_confidence_engine_v1",
        "generated_at": now(),
        "confidence": confidence,
        "confidencePct": round(confidence * 100, 2),
        "label": "Execution",
        "orders_count": len(orders),
        "action_policy": action_policy,
        "real_execution_authorized": allow_real,
        "simulated_execution_authorized": allow_simulated,
        "checks": [
            {"name": name, "passed": passed, "weight": weight}
            for name, passed, weight in checks
        ],
        "sources": {k: str(v) for k, v in SOURCES.items()},
    }

    save(OUT, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
