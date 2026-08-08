from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

POLICY_PATH = Path("data/capital/policies/capital_policy.json")


def load_policy(path: Path = POLICY_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing capital policy: {path}")
    with path.open("r", encoding="utf-8") as f:
        policy = json.load(f)
    if not isinstance(policy, dict):
        raise ValueError("capital_policy must be a JSON object")
    return policy


def get_phase(policy: Dict[str, Any], nav_eur: float) -> Dict[str, Any]:
    phases = policy.get("phases", [])
    for phase in phases:
        min_nav = float(phase.get("min_nav_eur", 0) or 0)
        max_nav = phase.get("max_nav_eur")
        if nav_eur >= min_nav and (max_nav is None or nav_eur < float(max_nav)):
            return phase
    return phases[-1] if phases else {}
