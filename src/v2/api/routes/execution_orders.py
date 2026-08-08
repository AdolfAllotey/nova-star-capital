from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(tags=["execution-orders"])

EXECUTION_PLAN_PATH = Path("/opt/nsc/data/preprod/trading/execution_plan.json")


def load_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@router.get("/api/execution-orders")
def get_execution_orders() -> Dict[str, Any]:
    plan = load_json(EXECUTION_PLAN_PATH)
    orders = plan.get("orders", []) if isinstance(plan.get("orders"), list) else []

    return {
        "status": plan.get("status", "unknown"),
        "env": plan.get("env"),
        "generated_at": plan.get("generated_at") or plan.get("updated_at") or plan.get("ts"),
        "source": str(EXECUTION_PLAN_PATH),
        "execution_mode": plan.get("execution_mode") or "SIMULATED_ONLY",
        "orders_count": len(orders),
        "orders": orders,
        "blocked_orders_count": sum(1 for o in orders if o.get("blocked_by")),
        "simulated_only_count": sum(
            1 for o in orders
            if str(o.get("execution_mode") or o.get("action") or "").upper() == "SIMULATED_ONLY"
        ),
        "symbols": [o.get("symbol") for o in orders if isinstance(o, dict) and o.get("symbol")],
    }
