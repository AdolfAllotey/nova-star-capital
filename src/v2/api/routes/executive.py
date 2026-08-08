from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["executive"])

@router.get("/api/executive/overview")
def executive_overview():
    return {
        "status": "ok",
        "current_pnl": 0,
        "peak_pnl": 0,
        "drawdown": 0,
        "drawdown_pct": 0,
        "curve_points": 0,
        "capital": 10000,
        "mode": "PREPROD",
        "timestamp": datetime.utcnow().isoformat()
    }
