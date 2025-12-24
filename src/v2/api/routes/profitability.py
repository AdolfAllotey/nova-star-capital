# src/v2/api/routes/profitability.py

from fastapi import APIRouter, HTTPException
from src.v2.utils.file_utils import load_json_file

router = APIRouter()


@router.get("/profitability/monthly")
async def get_monthly_profitability():
    """
    Renvoie les séries mensuelles PnL + coûts.
    Utilisé par la page Profitability pour les graphiques.
    """
    pnl = load_json_file("src/v2/data/reports/monthly_pnl.json", default={})
    costs = load_json_file("src/v2/data/reports/monthly_costs.json", default={})

    if not pnl and not costs:
        # Pas de données -> 404 propre
        raise HTTPException(status_code=404, detail="No profitability data")

    return {
        "pnl": pnl,
        "costs": costs,
    }


@router.get("/profitability/summary")
async def get_profitability_summary():
    """
    Résumé global (totaux + net).
    Utilisé pour les cartes KPI en haut de page.
    """
    summary = load_json_file(
        "src/v2/data/reports/profitability_summary.json", default={}
    )

    if not summary:
        # Fallback safe si le fichier n’existe pas encore
        return {
            "total_pnl": 0,
            "total_costs": 0,
            "net": 0,
            "currency": "EUR",
        }

    return summary
