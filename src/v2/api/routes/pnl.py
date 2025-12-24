from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file

router = APIRouter()
logger = get_logger(__name__)
PNL_PATH = "src/v2/data/reports/monthly_pnl.json"

class PnLResponse(BaseModel):
    equity: float = Field(..., description="Valeur actuelle de l'equity")
    pnl_cum: float = Field(..., description="PnL cumulé (net)")
    last_update: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)

@router.get("/pnl", response_model=PnLResponse)
def get_pnl_status():
    data = load_json_file(PNL_PATH, default={})
    if not data:
        raise HTTPException(status_code=404, detail="PNL non disponible")
    equity = float(data.get("equity") or data.get("equity_now") or 0.0)
    pnl_cum = float(data.get("pnl_cum") or data.get("pnl_total") or data.get("pnl") or 0.0)
    last_update = data.get("last_update") or data.get("updated_at") or datetime.utcnow().isoformat()
    return PnLResponse(equity=equity, pnl_cum=pnl_cum, last_update=last_update, raw=data)
