from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter(tags=["offensive-overview"])

import os

ROOT = Path(os.getenv("NSC_DATA_DIR", "/opt/nsc/data/preprod"))

UI_BUNDLE_PATH = ROOT / "equities_offensive/ui/ui_bundle.json"
EXECUTION_PLAN_PATH = ROOT / "equities_offensive/execution/execution_plan.json"
LIMITS_REPORT_PATH = ROOT / "equities_offensive/state/limits_report.json"
RECON_REPORT_PATH = ROOT / "equities_offensive/state/reconciliation_report.json"
EXPOSURE_PATH = ROOT / "equities_offensive/state/exposure_snapshot.json"


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


@router.get("/bricks/offensive/overview")
def offensive_overview() -> Dict[str, Any]:
    ui_bundle = load_json(UI_BUNDLE_PATH, {}) or {}
    execution_plan = load_json(EXECUTION_PLAN_PATH, {}) or {}
    limits_report = load_json(LIMITS_REPORT_PATH, {}) or {}
    reconciliation_report = load_json(RECON_REPORT_PATH, {}) or {}
    exposure_snapshot = load_json(EXPOSURE_PATH, {}) or {}

    kpis = ui_bundle.get("kpis", {}) if isinstance(ui_bundle, dict) else {}
    if not isinstance(kpis, dict):
        kpis = {}

    return {
        "header": {
            "name": "Actions Offensives",
            "status": "PREPROD",
            "env": "PREPROD",
            "mode": kpis.get("action_policy", "SIMULATED_ONLY"),
            "regime": kpis.get("regime", "UNKNOWN"),
            "regimeConfidence": kpis.get("regime_confidence", 0),
            "planId": kpis.get("plan_id"),
        },
        "kpis": {
            "candidates": kpis.get("candidates_count", 0),
            "orders": kpis.get("orders_count", 0),
            "openPositions": kpis.get("open_positions", 0),
            "totalNotionalUsd": kpis.get("total_notional_usd", 0),
            "limitsOk": kpis.get("limits_ok", True),
            "softVetos": kpis.get("soft_vetos", []) or [],
        },
        "pipeline": {
            "candidateOrders": execution_plan.get("candidate_orders", []) or [],
            "orders": execution_plan.get("orders", []) or [],
            "reasons": execution_plan.get("reasons", []) or [],
            "planId": execution_plan.get("plan_id"),
            "actionPolicy": execution_plan.get("action_policy"),
        },
        "risk": limits_report if isinstance(limits_report, dict) else {},
        "reconciliation": reconciliation_report if isinstance(reconciliation_report, dict) else {},
        "exposure": exposure_snapshot if isinstance(exposure_snapshot, dict) else {},
    }
