from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file

router = APIRouter()
logger = get_logger(__name__)
TRADE_SIM_PATH = "src/v2/data/trades/trade_simulation.json"
OPEN_POS_PATH  = "src/v2/data/trades/open_positions.json"

class TradeItem(BaseModel):
    id: Optional[str] = None
    token: Optional[str] = None
    side: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    amount: Optional[float] = None
    exchange: Optional[str] = None
    pnl: Optional[float] = None
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class TradesResponse(BaseModel):
    simulated: List[TradeItem] = Field(default_factory=list)
    open_positions: List[TradeItem] = Field(default_factory=list)
    count_simulated: int = 0
    count_open: int = 0

def _to_float(v):
    try: return float(v)
    except Exception: return None

def _normalize_list(raw, to_trade):
    if isinstance(raw, list):
        return [to_trade(x) for x in raw]
    return []

@router.get("/trades", response_model=TradesResponse)
def get_trades():
    sim = load_json_file(TRADE_SIM_PATH, default=[])
    opens = load_json_file(OPEN_POS_PATH, default=[])
    if isinstance(sim, dict):   sim = sim.get("trades", [])
    if isinstance(opens, dict): opens = opens.get("open_positions", [])
    def to_trade(item):
        return TradeItem(
            id=item.get("id") or item.get("trade_id"),
            token=item.get("token") or item.get("symbol"),
            side=item.get("side"),
            entry_price=_to_float(item.get("entry_price")),
            exit_price=_to_float(item.get("exit_price")),
            amount=_to_float(item.get("amount")),
            exchange=item.get("exchange"),
            pnl=_to_float(item.get("pnl")),
            opened_at=item.get("opened_at") or item.get("timestamp") or item.get("time"),
            closed_at=item.get("closed_at"),
            meta=item
        )
    sim_norm  = _normalize_list(sim, to_trade)
    open_norm = _normalize_list(opens, to_trade)
    return TradesResponse(simulated=sim_norm, open_positions=open_norm,
                          count_simulated=len(sim_norm), count_open=len(open_norm))
