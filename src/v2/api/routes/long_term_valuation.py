from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

VAL_PATH = Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json")

def _read_json(path: Path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

@router.get("/long-term/valuation", summary="Long Term valuation")
def get_long_term_valuation():
    data = _read_json(VAL_PATH)
    if not data:
        raise HTTPException(status_code=404, detail="lt_portfolio_valuation unavailable")
    return data
