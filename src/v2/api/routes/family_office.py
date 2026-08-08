from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter


router = APIRouter()

BUNDLE_PATH = Path("data/capital/family_office_bundle.json")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "source": str(path)
        }


@router.get("/family-office")
def get_family_office_bundle() -> Dict[str, Any]:
    data = read_json(BUNDLE_PATH, default={}) or {}
    if not data:
        return {
            "status": "missing",
            "engine": "family_office_api_v1",
            "source": str(BUNDLE_PATH),
            "message": "family_office_bundle.json not found or empty"
        }

    data["api"] = {
        "route": "/api/family-office",
        "engine": "family_office_api_v1",
        "source": str(BUNDLE_PATH)
    }
    return data
