from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter

router = APIRouter(tags=["execution-trace"])

DATA_DIR = Path("/opt/nsc/data/preprod")
PLAN_PATH = DATA_DIR / "trading" / "execution_plan.json"
SIM_PLAN_PATH = DATA_DIR / "trading" / "execution_plan_simulated.json"
SIZED_SIGNALS_PATH = DATA_DIR / "trading" / "sized_signals.json"
SIGNAL_CANDIDATES_PATH = DATA_DIR / "analysis" / "signal_candidates.json"


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def as_list(doc: Any) -> List[Dict[str, Any]]:
    if isinstance(doc, list):
        return [x for x in doc if isinstance(x, dict)]
    if isinstance(doc, dict):
        for key in ("orders", "signals", "candidates", "items"):
            val = doc.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
    return []


def num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v or default)
    except Exception:
        return default


@router.get("/api/execution-trace")
def execution_trace() -> Dict[str, Any]:
    plan = load_json(PLAN_PATH, {}) or {}
    sim_plan = load_json(SIM_PLAN_PATH, {}) or {}
    sized_doc = load_json(SIZED_SIGNALS_PATH, []) or []
    candidate_doc = load_json(SIGNAL_CANDIDATES_PATH, []) or []

    orders = as_list(plan)
    sim_orders = as_list(sim_plan)
    sized = as_list(sized_doc)
    candidates = as_list(candidate_doc)

    plan_symbols = {str(o.get("symbol", "")).lower(): o for o in orders}
    sim_symbols = {str(o.get("symbol", "")).lower(): o for o in sim_orders}
    sized_symbols = {str(o.get("symbol", "")).lower(): o for o in sized}

    rows: List[Dict[str, Any]] = []

    source_rows = candidates or sized or orders

    for item in source_rows:
        symbol = str(item.get("symbol") or "").lower()
        order = plan_symbols.get(symbol) or sim_symbols.get(symbol) or {}
        sized_row = sized_symbols.get(symbol) or {}

        blocked_by = order.get("blocked_by") or item.get("blocked_by") or []
        if not isinstance(blocked_by, list):
            blocked_by = [str(blocked_by)]

        execution_mode = order.get("execution_mode") or order.get("action") or plan.get("execution_mode") or "SIMULATED_ONLY"
        is_blocked = bool(blocked_by) or str(execution_mode).upper() in ("BLOCKED", "SKIPPED")

        rows.append({
            "symbol": symbol or item.get("symbol"),
            "side": order.get("side") or item.get("side") or "buy",
            "qty": order.get("qty"),
            "score": item.get("meta_score_pro") or item.get("meta_score") or item.get("score"),
            "reason": order.get("reason") or item.get("reason"),
            "signal_status": "DETECTED",
            "candidate_status": "CANDIDATE",
            "sizing_status": "SIZED" if symbol in sized_symbols else "NOT_SIZED",
            "execution_status": "BLOCKED" if is_blocked else "EXECUTABLE",
            "execution_mode": execution_mode,
            "blocked_by": blocked_by,
            "exchange": order.get("exchange"),
            "notional_eur": order.get("notional") or order.get("notional_eur") or sized_row.get("notional_eur"),
            "risk_flag": order.get("risk_flag") or sized_row.get("risk_flag") or item.get("risk_flag"),
            "strategy": order.get("strategy") or item.get("strategy"),
        })

    return {
        "header": {
            "planId": plan.get("plan_id") or sim_plan.get("plan_id"),
            "actionPolicy": plan.get("action_policy") or plan.get("execution_mode") or "SIMULATED_ONLY",
            "generatedAt": plan.get("generated_at") or sim_plan.get("generated_at"),
            "reasons": plan.get("reasons") or [
                "crypto execution trace built from signal_candidates, sized_signals and execution_plan",
                "SIMULATED_ONLY orders are intentionally marked as blocked for real execution",
            ],
            "source": str(PLAN_PATH),
        },
        "rows": rows,
    }
