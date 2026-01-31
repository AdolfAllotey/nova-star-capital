from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter

from src.v2.utils.file_utils import load_json_file

router = APIRouter(prefix="/governance", tags=["governance"])


def _data_root() -> Path:
    dr = os.getenv("DATA_ROOT")
    if dr:
        return Path(dr)
    p = Path("/opt/nsc/app/data")
    if p.exists():
        return p
    return Path.cwd() / "data"


@router.get("/status")
def governance_status():
    data_root = _data_root()
    path = data_root / "analysis" / "governance_engine_pro.json"
    data = load_json_file(path, default={})

    action_policy = (data.get("action_policy") or data.get("policy", {}).get("action_policy") or "UNKNOWN") if isinstance(data, dict) else "UNKNOWN"
    mode = (data.get("mode") or data.get("flag") or "UNKNOWN") if isinstance(data, dict) else "UNKNOWN"

    return {
        "ok": True if isinstance(data, dict) and data else False,
        "env": os.getenv("NSC_ENV", "UNKNOWN"),
        "data_root": str(data_root),
        "path": str(path),
        "exists": path.exists(),
        "hard_block": bool((data or {}).get("hard_block", False)) if isinstance(data, dict) else False,
        "soft_veto": (data or {}).get("soft_veto") if isinstance(data, dict) else None,
        "action_policy": str(action_policy).upper() if action_policy else "UNKNOWN",
        "mode": str(mode),
        "caps": (data or {}).get("caps") if isinstance(data, dict) else None,
        "as_of": (data or {}).get("as_of") or (data or {}).get("timestamp"),
    }
