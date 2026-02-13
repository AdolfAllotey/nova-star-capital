# src/v2/api/routes/profitability.py

from fastapi import APIRouter
from datetime import datetime, timezone

from src.v2.utils.file_utils import load_json_file

router = APIRouter()


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/profitability/monthly")
async def get_monthly_profitability():
    """
    Renvoie les séries mensuelles PnL + coûts.
    Utilisé par la page Profitability pour les graphiques.
    """
    pnl = load_json_file("data/reports/monthly_pnl.json", default={})
    costs = load_json_file("data/reports/monthly_costs.json", default={})

    # Normalisation: accepte dict {"YYYY-MM": value} ou liste [{"month":..., "pnl":...}, ...]
    pnl_map = {}
    if isinstance(pnl, dict):
        pnl_map = pnl
    elif isinstance(pnl, list):
        for row in pnl:
            if isinstance(row, dict) and row.get("month") is not None:
                pnl_map[str(row["month"])] = float(row.get("pnl", 0) or 0)

    costs_map = {}
    if isinstance(costs, dict):
        costs_map = costs
    elif isinstance(costs, list):
        for row in costs:
            if isinstance(row, dict) and row.get("month") is not None:
                costs_map[str(row["month"])] = float(row.get("costs", 0) or 0)

    if not pnl_map and not costs_map:
        return {
            "updated_at": _utc_now_iso(),
            "monthly": [],
            "message": "Aucune donnée disponible (monthly_pnl.json / monthly_costs.json).",
        }

    months = sorted(set(list(pnl_map.keys()) + list(costs_map.keys())))
    monthly = []
    for m in months:
        p = float(pnl_map.get(m, 0) or 0)
        c = float(costs_map.get(m, 0) or 0)
        monthly.append({"month": m, "pnl": p, "costs": c, "net": p - c})

    return {"updated_at": _utc_now_iso(), "monthly": monthly, "message": None}


@router.get("/profitability/summary")
async def get_profitability_summary():
    summary = load_json_file("data/reports/profitability_summary.json", default={})
    if not summary:
        return {"total_pnl": 0, "total_costs": 0, "net": 0, "currency": "EUR"}
    return summary
