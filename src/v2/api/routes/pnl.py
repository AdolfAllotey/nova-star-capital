from fastapi import APIRouter

router = APIRouter(tags=["pnl"])

@router.get("/pnl/recent")
def pnl_recent():
    return {
        "series": [],
        "unit": "€"
    }
