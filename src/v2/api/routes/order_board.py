from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter(tags=["order-board"])

EXECUTION_PLAN_PATH = Path("data/equities_offensive/execution/execution_plan.json")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


@router.get("/api/order-board")
def order_board() -> Dict[str, Any]:
    plan = load_json(EXECUTION_PLAN_PATH, {}) or {}

    return {
        "header": {
            "planId": plan.get("plan_id"),
            "actionPolicy": plan.get("action_policy", "N/A"),
            "reasons": plan.get("reasons", []) or [],
        },
        "candidateOrders": plan.get("candidate_orders", []) or [],
        "executableOrders": plan.get("orders", []) or [],
    }
