from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

CAPITAL_STATE_PATH = Path("data/capital/capital_state.json")
OUTPUT_PATH = Path("data/capital/survival_state.json")


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
    state = read_json(CAPITAL_STATE_PATH, default={}) or {}

    survival = {
        "status": "ok",
        "engine": "survival_engine_v1",
        "mode": "NORMAL",
        "hard_block": False,
        "actions": [],
        "checks": {
            "nav_available": float(state.get("total_nav_eur", 0.0) or 0.0) > 0,
            "collateral_policy_active": True,
            "crypto_collateral_blocked": True
        }
    }

    write_json(OUTPUT_PATH, survival)
    return survival


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
