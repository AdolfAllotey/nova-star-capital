from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()

METALS_SIGNAL_PATH = Path("/opt/nsc/app/src/v2/data/precious_metals/metals_signal.json")
PORTFOLIO_STATE_PATH = Path("/opt/nsc/app/src/v2/data/portfolio/state/portfolio_state.json")


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@router.get("/api/precious-metals/signal")
def get_precious_metals_signal():
    signal = load_json(METALS_SIGNAL_PATH)
    portfolio_state = load_json(PORTFOLIO_STATE_PATH)

    brick_state = portfolio_state.get("bricks", {}).get("precious_metals", {})

    return {
        "brick": "precious_metals",
        "signal": signal,
        "portfolio_state": brick_state
    }
