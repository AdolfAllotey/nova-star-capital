from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

VAL_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json")

@router.get("/lt-curve", summary="NSC LT curve v1")
def get_lt_curve():
    if not VAL_PATH.exists():
        raise HTTPException(status_code=404, detail="lt valuation unavailable")

    try:
        data = json.loads(VAL_PATH.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"invalid lt valuation source: {exc}")

    totals = data.get("totals", {}) or {}
    invested = float(totals.get("invested_eur", 0.0) or 0.0)
    market_value = float(totals.get("market_value_eur", 0.0) or 0.0)
    updated_at = data.get("updated_at") or data.get("timestamp") or "n/a"

    points = [
        {
            "date": "Invested",
            "cumulative_profit": round(invested, 2),
        },
        {
            "date": "Current",
            "cumulative_profit": round(market_value, 2),
        },
    ]

    return {
        "status": "ok",
        "engine": "lt_curve_v1",
        "points": points,
        "final_cumulative_profit": round(market_value, 2),
        "updated_at": updated_at,
    }
