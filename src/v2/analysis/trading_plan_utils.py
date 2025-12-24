"""
trading_plan_utils.py
---------------------------------
Utilitaires pour charger et exposer le plan de trading structuré
(data/trading/trading_plan.json).

Permet :
  - de charger le plan complet
  - de récupérer les checklists par phase
  - de l'exposer via l'API ou de le consommer côté LLM
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("trading_plan_utils")

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = ROOT_DIR / "data"
TRADING_DIR = DATA_DIR / "trading"

TRADING_PLAN_FILE = TRADING_DIR / "trading_plan.json"

logger.info(f"[trading_plan_utils] ROOT_DIR={ROOT_DIR}, DATA_DIR={DATA_DIR}")

# ---------------------------------------------------------------------------
# file_utils fallback
# ---------------------------------------------------------------------------

try:
    from src.v2.utils.file_utils import load_json_file  # type: ignore
except Exception:  # pragma: no cover
    load_json_file = None

    import json

    def _load_json(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Erreur lors du chargement JSON: %s", path)
            return default
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def load_trading_plan(default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Charge le plan de trading structuré.
    """
    if default is None:
        default = {}
    data = _load_json(TRADING_PLAN_FILE, default=default)
    if not isinstance(data, dict):
        logger.warning(
            "[trading_plan_utils] Format inattendu pour %s (attendu dict).",
            TRADING_PLAN_FILE,
        )
        return default
    return data


def get_phase(plan: Dict[str, Any], phase_key: str) -> Optional[Dict[str, Any]]:
    """
    Récupère une phase particulière (pre_trade, entry, exit, etc.)
    """
    phases = plan.get("phases")
    if not isinstance(phases, dict):
        return None
    phase = phases.get(phase_key)
    if not isinstance(phase, dict):
        return None
    return phase


def get_checklist(plan: Dict[str, Any], phase_key: str) -> List[str]:
    """
    Retourne la checklist d'une phase, ou [] si non trouvée.
    """
    phase = get_phase(plan, phase_key)
    if not phase:
        return []
    checklist = phase.get("checklist")
    if not isinstance(checklist, list):
        return []
    return [str(item) for item in checklist]


if __name__ == "__main__":
    # Petit test manuel
    p = load_trading_plan()
    pre_trade = get_checklist(p, "pre_trade")
    logger.info("[trading_plan_utils] Checklist pre_trade: %s", pre_trade)
