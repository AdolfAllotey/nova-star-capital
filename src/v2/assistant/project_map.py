"""
src/v2/assistant/project_map.py

Expose une "carte" du projet NSC pour l'assistant autonome.

Structure retournée par get_project_map() :

{
  "config": {...},
  "analysis_engines": {...},
  "trading_tasks": {...},
  "api_routes": {...},
  "react_pages": {...}
}

- Utilise get_config() pour récupérer root_dir, data_dir, etc.
- CLI :
    python -m src.v2.assistant.project_map
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from .config import get_config

logger = logging.getLogger(__name__)


def get_project_map() -> Dict[str, Any]:
    """
    Retourne la "carte" du projet pour l'assistant autonome.
    """
    cfg = get_config()

    project_map: Dict[str, Any] = {
        "config": cfg,
        "analysis_engines": {
            "narrative_engine": {
                "module": "src.v2.analysis.narrative_engine_light",
                "entrypoint": "main",
                "output_file": "data/analysis/narrative_overview.json",
            },
            "hype_cycle_engine": {
                "module": "src.v2.analysis.hype_cycle_engine_light",
                "entrypoint": "main",
                "output_file": "data/analysis/hype_cycle_overview.json",
            },
            "liquidity_risk_engine": {
                "module": "src.v2.analysis.liquidity_risk_engine_light",
                "entrypoint": "main",
                "output_file": "data/analysis/liquidity_risk_overview.json",
            },
            "weak_signals_engine": {
                "module": "src.v2.analysis.weak_signals_engine_light",
                "entrypoint": "main",
                "output_file": "data/analysis/weak_signals_overview.json",
            },
            "anomalies_engine": {
                "module": "src.v2.analysis.anomalies_engine_light",
                "entrypoint": "main",
                "output_file": "data/analysis/anomalies_overview.json",
            },
            "discipline_engine": {
                "module": "src.v2.analysis.discipline_engine_light",
                "entrypoint": "main",
                "output_file": "data/analysis/discipline_overview.json",
            },
            "daily_trading_feedback": {
                "module": "src.v2.analysis.daily_trading_feedback",
                "entrypoint": "main",
                "output_file": "data/analysis/daily_feedback.json",
            },
        },
        "trading_tasks": {
            "daily_trading_loop": {
                "module": "src.v2.trading.daily_trading_loop",
                "entrypoint": "main",
                "description": "Boucle quotidienne complète NSC (snapshot marché, moteurs light, feedback, etc.)",
            }
        },
        "api_routes": {
            "root": "/",
            "market": {
                "overview": "/market/overview",
                "regime": "/market/regime",
                "top_movers": "/market/top-movers",
            },
            "profitability": {
                "monthly": "/profitability/monthly",
            },
            "trading": {
                "worst_trades": "/worst-trades",
                "open_positions": "/open-positions",
            },
            "ico": {
                "candidates": "/ico/candidates",
                "screened": "/ico/screened",
                "scored": "/ico/scored",
                "allocation": "/ico/allocation",
            },
            "sentiment": {
                "overview": "/sentiment/overview",
            },
            "whales": {
                "leaderboard": "/whales/leaderboard",
            },
            "analysis": {
                "daily_feedback": "/analysis/daily-feedback",
                "anomalies": "/analysis/anomalies",
            },
            "metrics": "/metrics",
        },
        "react_pages": {
            "dashboard": [
                "src/v2/interface/react/src/pages/Dashboard.jsx",
                "src/v2/interface/react/src/pages/Profitability.jsx",
            ],
            "risk": [
                "src/v2/interface/react/src/pages/WorstTrades.jsx",
                "src/v2/interface/react/src/pages/OpenPositions.jsx",
            ],
            "ico": [
                "src/v2/interface/react/src/pages/ICODashboard.jsx",
            ],
            "meta": [
                "src/v2/interface/react/src/pages/MetaConsole.jsx",
            ],
        },
    }

    return project_map


def main() -> None:
    """
    Entrée CLI : python -m src.v2.assistant.project_map

    Affiche la project map complète en JSON.
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s:%(name)s:%(message)s",
        )

    pm = get_project_map()
    logger.info("[assistant.project_map] Project map générée.")
    print(json.dumps(pm, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
