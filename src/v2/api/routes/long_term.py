from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

LT_PATH = Path("/opt/nsc/app/data/portfolio/lt_portfolio.json")

def _read_json(path: Path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

@router.get("/long-term", summary="Long Term portfolio")
def get_long_term():
    data = _read_json(LT_PATH)
    if not data:
        raise HTTPException(status_code=404, detail="lt_portfolio unavailable")
    return data
