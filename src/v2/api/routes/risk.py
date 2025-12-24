# app/src/v2/api/routes/risk.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import os, json, datetime as dt

router = APIRouter(prefix="/risk", tags=["risk"])

DATA_ROOT = os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data")
WORST_PATH = os.path.join(DATA_ROOT, "risk", "worst_trades.json")

class WorstTrade(BaseModel):
    token: str
    loss_eur: float
    reason: Optional[str] = None
    ts: Optional[str] = None

class WorstTradesResp(BaseModel):
    updated_at: Optional[str] = None
    items: List[WorstTrade] = []
    message: Optional[str] = None

def _read_json(path: str) -> Any:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None

@router.get("/worst-trades", response_model=WorstTradesResp)
def get_worst_trades():
    raw = _read_json(WORST_PATH)
    items: List[Dict] = []
    if isinstance(raw, dict) and "items" in raw and isinstance(raw["items"], list):
        items = raw["items"]
    elif isinstance(raw, list):
        items = raw
    else:
        return WorstTradesResp(
            updated_at=dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            items=[],
            message="Aucune donnée (risk/worst_trades.json).",
        )

    norm: List[WorstTrade] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        token = str(it.get("token") or it.get("symbol") or it.get("asset") or "").upper()
        # accepte loss ou pnl négatif
        loss = it.get("loss_eur")
        if loss is None:
            pnl = it.get("pnl_eur") or it.get("pnl") or 0
            try:
                pnl = float(pnl)
            except Exception:
                pnl = 0.0
            loss = pnl if pnl < 0 else -abs(pnl)
        try:
            loss = float(loss)
        except Exception:
            continue
        norm.append(WorstTrade(
            token=token or "UNKNOWN",
            loss_eur=float(loss),
            reason=it.get("reason") or it.get("explain"),
            ts=it.get("ts") or it.get("timestamp"),
        ))

    # trier par perte la plus forte (plus négatif d'abord)
    norm.sort(key=lambda x: x.loss_eur)
    return WorstTradesResp(
        updated_at=dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        items=norm,
        message=None if norm else "Fichier présent mais vide.",
    )
