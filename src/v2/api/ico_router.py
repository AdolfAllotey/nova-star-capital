import os
import json
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/ico", tags=["ico"])

DATA_ROOT = (
    os.environ.get("NSC_DATA_DIR")
    or os.environ.get("DATA_DIR")
    or os.environ.get("NSC_DATA_ROOT")
    or "/opt/nsc/app/data"
)

ICO_DIR = os.path.join(DATA_ROOT, "ico")
ICO_CANDIDATES_PATH = os.path.join(ICO_DIR, "ico_candidates.json")
ICO_SCREENED_PATH   = os.path.join(ICO_DIR, "ico_screened.json")
ICO_SCORED_PATH     = os.path.join(ICO_DIR, "ico_scored.json")
ICO_ALLOCATION_PATH = os.path.join(ICO_DIR, "ico_allocation.json")
ICO_STATUS_PATH     = os.path.join(ICO_DIR, "ico_status.json")


def _read_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


@router.get("")
def ico_root() -> Dict[str, Any]:
    return {"ok": True, "endpoints": ["", "/candidates", "/screened", "/scored", "/allocation", "/status"]}


@router.get("/candidates")
def ico_candidates() -> Any:
    return _read_json(ICO_CANDIDATES_PATH, default={"items": [], "updated_at": None})


@router.get("/screened")
def ico_screened() -> Any:
    return _read_json(ICO_SCREENED_PATH, default={"items": [], "updated_at": None})


@router.get("/scored")
def ico_scored() -> Any:
    return _read_json(ICO_SCORED_PATH, default={"items": [], "updated_at": None})


@router.get("/allocation")
def ico_allocation() -> Any:
    return _read_json(ICO_ALLOCATION_PATH, default={"items": [], "updated_at": None})


@router.get("/status")
def ico_status() -> Any:
    return _read_json(
        ICO_STATUS_PATH,
        default={
            "ok": False,
            "updated_at": None,
            "generated_at": None,
            "counts": None,
            "notes": ["missing_ico_status"],
        },
    )
