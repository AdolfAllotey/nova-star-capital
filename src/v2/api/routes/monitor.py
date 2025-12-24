from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file

router = APIRouter()
logger = get_logger(__name__)
WHALES_PATH = "src/v2/data/monitoring/whale_activity.json"

class WhaleEvent(BaseModel):
    wallet: Optional[str] = None
    action: Optional[str] = None
    token: Optional[str] = None
    amount: Optional[float] = None
    value_eur: Optional[float] = None
    exchange: Optional[str] = None
    timestamp: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class WhalesResponse(BaseModel):
    events: List[WhaleEvent] = Field(default_factory=list)
    count: int = 0

def _to_float(v):
    try: return float(v)
    except Exception: return None

@router.get("/whales", response_model=WhalesResponse)
def get_whales():
    data = load_json_file(WHALES_PATH, default=[])
    if isinstance(data, dict):
        data = data.get("events") or data.get("items") or []
    def to_evt(x):
        return WhaleEvent(
            wallet=x.get("wallet") or x.get("address"),
            action=x.get("action") or x.get("type"),
            token=x.get("token") or x.get("symbol"),
            amount=_to_float(x.get("amount")),
            value_eur=_to_float(x.get("value_eur") or x.get("value")),
            exchange=x.get("exchange"),
            timestamp=x.get("timestamp") or x.get("time"),
            meta=x
        )
    norm = [to_evt(x) for x in (data if isinstance(data, list) else [])]
    norm.sort(key=lambda e: (e.timestamp or ""), reverse=True)
    return WhalesResponse(events=norm, count=len(norm))
