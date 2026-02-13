from __future__ import annotations

from typing import Any, Dict
from pathlib import Path

GOV_PATH = Path("data/governance/governance_engine_pro.json")

def _load_json(path: Path, default: Any):
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        import json
        return json.loads(path.read_text(encoding="utf-8"))

def load_governance(scope: str = "equities_offensive") -> Dict[str, Any]:
    """
    Returns merged governance for a given scope:
      - global: mode, action_policy, caps
      - scope override: gov["scopes"][scope]
    """
    gov = _load_json(GOV_PATH, default={}) or {}
    if not isinstance(gov, dict):
        gov = {}

    out: Dict[str, Any] = {
        "mode": gov.get("mode", "UNKNOWN"),
        "action_policy": (gov.get("action_policy") or "SIMULATED_ONLY"),
        "caps": gov.get("caps", {}) if isinstance(gov.get("caps"), dict) else {},
        "scope": scope,
        "source_path": str(GOV_PATH),
        "enabled": True,
    }

    scopes = gov.get("scopes")
    if isinstance(scopes, dict):
        sc = scopes.get(scope)
        if isinstance(sc, dict):
            out["enabled"] = bool(sc.get("enabled", True))
            if "action_policy" in sc:
                out["action_policy"] = sc.get("action_policy") or out["action_policy"]
            if isinstance(sc.get("caps"), dict):
                merged = dict(out["caps"])
                merged.update(sc["caps"])
                out["caps"] = merged

    return out
