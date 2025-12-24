# app/src/v2/api/routes/reports.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os, json, datetime as dt

router = APIRouter(prefix="/reports", tags=["reports"])

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
PNL_PATH   = os.path.join(DATA_ROOT, "reports", "monthly_pnl.json")
COSTS_PATH = os.path.join(DATA_ROOT, "reports", "monthly_costs.json")

class ProfitabilityRow(BaseModel):
    month: str          # "2025-11"
    pnl: float = 0.0
    costs: float = 0.0
    net: float = 0.0

class ProfitabilityResp(BaseModel):
    updated_at: Optional[str] = None
    monthly: List[ProfitabilityRow] = []
    message: Optional[str] = None

def _read_json(path: str) -> Any:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None

@router.get("/profitability", response_model=ProfitabilityResp)
def get_profitability():
    pnl = _read_json(PNL_PATH) or []
    costs = _read_json(COSTS_PATH) or []

    # On accepte 2 formats:
    #  - liste de {month, value}
    #  - dict {"2025-11": value, ...}
    def to_map(obj, key_name="pnl"):
        m: Dict[str, float] = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                try:
                    m[str(k)] = float(v)
                except Exception:
                    pass
        elif isinstance(obj, list):
            for it in obj:
                if isinstance(it, dict):
                    month = str(it.get("month") or it.get("date") or it.get("period") or "")
                    val = it.get(key_name) if key_name in it else it.get("value", 0)
                    try:
                        if month:
                            m[month] = float(val)
                    except Exception:
                        pass
        return m

    pnl_map   = to_map(pnl,   key_name="pnl")
    costs_map = to_map(costs, key_name="costs")

    months = sorted(set(pnl_map.keys()) | set(costs_map.keys()))
    rows: List[ProfitabilityRow] = []
    for m in months:
        p = pnl_map.get(m, 0.0)
        c = costs_map.get(m, 0.0)
        rows.append(ProfitabilityRow(month=m, pnl=p, costs=c, net=p - c))

    return ProfitabilityResp(
        updated_at=dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        monthly=rows,
        message=None if rows else "Aucune donnée disponible (monthly_pnl.json / monthly_costs.json).",
    )
