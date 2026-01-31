from __future__ import annotations

import os
from pathlib import Path
from fastapi import APIRouter

from src.v2.utils.file_utils import load_json_file

router = APIRouter(prefix="/risk", tags=["risk"])


def _data_root() -> Path:
    dr = os.getenv("DATA_ROOT")
    if dr:
        return Path(dr)
    p = Path("/opt/nsc/app/data")
    if p.exists():
        return p
    return Path.cwd() / "data"


@router.get("/status")
def risk_status():
    data_root = _data_root()
    path_state = data_root / "analysis" / "risk_state_last.json"
    path_engine = data_root / "analysis" / "risk_engine_pro.json"

    state = load_json_file(path_state, default={})
    engine = load_json_file(path_engine, default={})

    flag = None
    risk_mode = None
    hard_block = None
    soft_veto = None

    if isinstance(state, dict) and state:
        flag = state.get("flag") or state.get("global_flag")
        risk_mode = state.get("risk_mode")
        hard_block = state.get("hard_block")
        soft_veto = state.get("soft_veto")

    if flag is None and isinstance(engine, dict) and engine:
        flag = engine.get("flag") or engine.get("global_flag")
    if risk_mode is None and isinstance(engine, dict) and engine:
        risk_mode = engine.get("risk_mode")
    if hard_block is None and isinstance(engine, dict) and engine:
        hard_block = engine.get("hard_block")
    if soft_veto is None and isinstance(engine, dict) and engine:
        soft_veto = engine.get("soft_veto")

    return {
        "ok": True,
        "env": os.getenv("NSC_ENV", "UNKNOWN"),
        "data_root": str(data_root),
        "risk_state_path": str(path_state),
        "risk_engine_path": str(path_engine),
        "risk_state_exists": path_state.exists(),
        "risk_engine_exists": path_engine.exists(),
        "flag": flag,
        "risk_mode": risk_mode,
        "hard_block": hard_block,
        "soft_veto": soft_veto,
        "as_of": (state.get("as_of") if isinstance(state, dict) else None)
                or (engine.get("timestamp") if isinstance(engine, dict) else None),
    }
