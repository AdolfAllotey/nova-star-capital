#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Any, Dict

def _read_json(path: Path) -> Dict[str, Any]:
    # Prefer project helper if available
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default={}) or {}
    except Exception:
        import json
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

def get_governance_path() -> Path:
    # Single source of truth: env override -> default path
    env_path = os.environ.get("NSC_GOVERNANCE_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Default in repo
    return Path("src/v2/data/governance/governance_engine_pro.json").resolve()

def load_governance() -> Dict[str, Any]:
    path = get_governance_path()
    if not path.exists():
        raise FileNotFoundError(f"Governance file not found: {path}")
    g = _read_json(path)

    # Minimal normalization / defaults
    g.setdefault("mode", "PREPROD")
    g.setdefault("action_policy", "SIMULATED_ONLY" if g["mode"] == "PREPROD" else "LIVE")
    g.setdefault("caps", {})
    g.setdefault("vetos", {})
    g["vetos"].setdefault("hard_block", [])
    g["vetos"].setdefault("soft_veto", [])
    g.setdefault("feature_flags", {})
    g["feature_flags"].setdefault("enforce_idempotency", True)
    g["feature_flags"].setdefault("require_execution_plan_validations", True)
    return g
