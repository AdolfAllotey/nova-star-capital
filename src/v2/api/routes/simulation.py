# app/src/v2/api/routes/simulation.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Any
import os, json, datetime as dt

router = APIRouter(prefix="/simulation", tags=["simulation"])

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
OPEN_POS_PATH = os.path.join(DATA_ROOT, "simulation", "open_positions.json")

class OpenPosition(BaseModel):
    token: str
    qty: float
    entry: float
    pnl: float
    exit_reason: Optional[str] = None
    ts: Optional[str] = None

class OpenPositionsResp(BaseModel):
    updated_at: Optional[str] = None
    open_positions: List[OpenPosition] = []
    message: Optional[str] = None

def _read_json(path: str) -> Any:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None

@router.get("/open-positions", response_model=OpenPositionsResp)
def get_open_positions():
    raw = _read_json(OPEN_POS_PATH)
    if not isinstance(raw, list):
        # tolère dict avec "items"
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            raw = raw["items"]
        else:
            return OpenPositionsResp(
                updated_at=dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                open_positions=[],
                message="Aucune position (simulation/open_positions.json).",
            )
    out: List[OpenPosition] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        try:
            out.append(OpenPosition(
                token=str(it.get("token") or it.get("symbol") or "").upper(),
                qty=float(it.get("qty") or it.get("quantity") or 0),
                entry=float(it.get("entry") or it.get("entry_price") or 0),
                pnl=float(it.get("pnl") or it.get("pnl_eur") or 0),
                exit_reason=it.get("exit_reason"),
                ts=it.get("ts") or it.get("timestamp"),
            ))
        except Exception:
            continue

    return OpenPositionsResp(
        updated_at=dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        open_positions=out,
        message=None if out else "Fichier présent mais vide.",
    )
