from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()

BOND_SIGNAL_PATH = Path("/opt/nsc/app/src/v2/data/bonds/bond_signal.json")
PORTFOLIO_STATE_PATH = Path("/opt/nsc/app/src/v2/data/portfolio/state/portfolio_state.json")


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@router.get("/api/bonds/signal")
def get_bonds_signal():
    signal = load_json(BOND_SIGNAL_PATH)
    portfolio_state = load_json(PORTFOLIO_STATE_PATH)

    brick_state = portfolio_state.get("bricks", {}).get("bonds", {})

    return {
        "brick": "bonds",
        "signal": signal,
        "portfolio_state": brick_state
    }
