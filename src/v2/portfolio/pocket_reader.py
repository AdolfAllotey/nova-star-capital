from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.v2.utils.file_utils import load_json_file
from src.v2.utils.logger import get_logger

logger = get_logger("pocket_reader")

POCKETS_PATH = Path("/opt/nsc/data/preprod/portfolio/pockets.json")

def get_budget_usd(scope: str, default: float = 0.0) -> float:
    data = load_json_file(str(POCKETS_PATH), default={}) or {}
    pockets = data.get("pockets", {})
    if not isinstance(pockets, dict):
        return float(default)
    item = pockets.get(scope, {})
    if not isinstance(item, dict):
        return float(default)
    try:
        return float(item.get("budget_eur", item.get("budget_usd", default)))
    except Exception:
        return float(default)

def get_all_budgets(default: float = 0.0) -> Dict[str, float]:
    data = load_json_file(str(POCKETS_PATH), default={}) or {}
    pockets = data.get("pockets", {})
    out: Dict[str, float] = {}
    if not isinstance(pockets, dict):
        return out
    for k, v in pockets.items():
        if isinstance(v, dict):
            try:
                out[k] = float(v.get("budget_eur", v.get("budget_usd", default)))
            except Exception:
                out[k] = float(default)
    return out
