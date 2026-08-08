from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.v2.capital.capital_policy_loader import load_policy, get_phase

CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
OUTPUT_PATH = Path("data/capital/capital_governor_decision.json")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run() -> Dict[str, Any]:
    policy = load_policy()
    state = read_json(CAPITAL_STATE_PATH, default={}) or {}

    nav = float(state.get("total_nav_eur", 0.0) or 0.0)
    phase = get_phase(policy, nav)
    phase_name = phase.get("name", "UNKNOWN")

    decision = {
        "status": "ok",
        "engine": "capital_governor_v1",
        "nav_eur": nav,
        "phase": phase_name,
        "distribution_after_tax": phase.get("distribution_after_tax", {}),
        "mode": phase_name,
        "priority_order": [
            "survival",
            "protection",
            "growth",
            "yield"
        ],
        "notes": [
            "Capital Governor decides where the next euro should go.",
            "Strategies propose; capital governance decides allocation."
        ]
    }

    write_json(OUTPUT_PATH, decision)
    return decision


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
