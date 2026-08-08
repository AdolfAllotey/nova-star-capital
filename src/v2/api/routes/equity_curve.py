from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

DATA_PATH = Path("/opt/nsc/src/v2/data/simulation/global_performance.json")

@router.get("/equity-curve", summary="NSC equity curve v1")
def get_equity_curve():
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="equity curve source unavailable")

    try:
        data = json.loads(DATA_PATH.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"invalid equity curve source: {exc}")

    history = data.get("history", [])
    cumulative_profit = 0.0
    points = []

    for row in history:
        daily_profit = float(row.get("daily_profit", 0.0) or 0.0)
        cumulative_profit += daily_profit
        points.append({
            "date": row.get("date"),
            "daily_profit": daily_profit,
            "cumulative_profit": round(cumulative_profit, 2),
        })

    return {
        "status": "ok",
        "engine": "equity_curve_v1",
        "source_file": str(DATA_PATH),
        "points": points,
        "final_cumulative_profit": round(cumulative_profit, 2),
    }
