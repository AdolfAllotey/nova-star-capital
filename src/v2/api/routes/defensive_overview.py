from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter(tags=["defensive-overview"])

DEFENSIVE_SIGNAL_PATH = Path("/opt/nsc/data/preprod/defensive/defensive_signal.json")
DEFENSIVE_ALLOCATIONS_PATH = Path("/opt/nsc/data/preprod/defensive/defensive_allocations.json")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


@router.get("/api/defensive_signal")
def defensive_signal() -> Dict[str, Any]:
    data = load_json(DEFENSIVE_SIGNAL_PATH, {})
    if not isinstance(data, dict):
        return {}
    return data


@router.get("/api/defensive_allocations")
def defensive_allocations() -> Dict[str, Any]:
    data = load_json(DEFENSIVE_ALLOCATIONS_PATH, {})
    if not isinstance(data, dict):
        return {"proposed_assets": []}
    return data
