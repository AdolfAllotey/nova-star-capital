from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter(tags=["pnl-state"])

PNL_STATE_PATH = Path("/opt/nsc/data/preprod/analysis/pnl_state.json")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


@router.get("/api/pnl-state")
def pnl_state() -> Dict[str, Any]:
    data = load_json(PNL_STATE_PATH, {})
    if not isinstance(data, dict):
        return {}
    return data
