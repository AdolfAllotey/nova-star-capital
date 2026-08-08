from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter

from src.v2.utils.file_utils import load_json_file

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _data_root() -> Path:
    for key in ("NSC_DATA_DIR", "NSC_DATA_ROOT", "DATA_DIR", "DATA_ROOT"):
        value = os.getenv(key)
        if value:
            return Path(value).expanduser().resolve()
    return Path("/opt/nsc/data/preprod").resolve()


@router.get("/backpressure")
def backpressure_status():
    data_root = _data_root()

    candidates = [
        data_root / "telemetry" / "backpressure_state.json",
        data_root / "telemetry" / "backpressure.json",
        data_root / "analysis" / "backpressure_engine_pro.json",
        data_root / "analysis" / "logs_overview_light.json",
    ]

    chosen = None
    payload = {}
    for p in candidates:
        if p.exists():
            chosen = p
            payload = load_json_file(p, default={})
            break

    return {
        "ok": True,
        "env": os.getenv("NSC_ENV", "UNKNOWN"),
        "data_root": str(data_root),
        "path": str(chosen) if chosen else None,
        "exists": bool(chosen),
        "data": payload if isinstance(payload, dict) else {"raw": payload},
    }
