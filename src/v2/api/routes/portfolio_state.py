from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

RUNTIME_FILE = Path("/opt/nsc/data/preprod/portfolio/state/portfolio_state.json")
SYNC_FILE = Path("/opt/nsc/app/src/v2/data/portfolio/state/portfolio_state.json")
LEGACY_FILE = Path("/opt/nsc/data/preprod/analysis/portfolio_state.json")
INITIAL_CAPITAL_PATH = Path("/opt/nsc/app/data/portfolio/initial_capital.json")


def _read_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_initial_capital():
    try:
        if INITIAL_CAPITAL_PATH.exists():
            payload = json.loads(INITIAL_CAPITAL_PATH.read_text(encoding="utf-8"))
            return float(payload.get("total_capital_eur", 0) or 0)
    except Exception:
        return 0.0
    return 0.0


@router.get(
    "/api/portfolio_state",
    summary="NSC portfolio state",
    operation_id="get_legacy_portfolio_state_underscore",
)
def get_portfolio_state():
    for path in (RUNTIME_FILE, SYNC_FILE, LEGACY_FILE):
        data = _read_json(path)
        if isinstance(data, dict) and data:
            return data

    raise HTTPException(status_code=404, detail="portfolio_state unavailable")


@router.get("/api/portfolio_capital", summary="NSC portfolio capital")
def get_portfolio_capital():
    return {
        "total_capital_eur": _load_initial_capital()
    }
