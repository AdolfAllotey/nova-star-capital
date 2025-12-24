# src/v2/analysis/cycle_engine_pro.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("cycle_engine_pro")

# ---------------------------------------------------------------------------
# Paths helpers
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = BASE_DIR / "data"


def get_paths() -> Tuple[Path, Path]:
    """
    Détermine ROOT_DIR et DATA_DIR de façon cohérente avec le reste du projet.

    - ROOT_DIR : /opt/nsc/app
    - DATA_DIR : /opt/nsc/app/data (ou NSC_DATA_DIR si défini)
    """
    root_dir = BASE_DIR
    data_env = os.getenv("NSC_DATA_DIR")
    if data_env:
        data_dir = Path(data_env).resolve()
    else:
        data_dir = DEFAULT_DATA_DIR
    return root_dir, data_dir


def _load(data_dir: Path, rel: str, default: Any) -> Any:
    """
    Helper pour charger un JSON relatif à DATA_DIR avec gestion de défaut.
    """
    path = data_dir / rel
    return load_json_file(str(path), default=default)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

DANGEROUS_PHASES = {"distribution", "capitulation"}
CAUTION_PHASES = {"choppy", "range", "late_cycle"}
BULL_PHASES = {"accumulation", "expansion", "markup", "trend_up"}
BEAR_PHASES = {"trend_down"}


def _classify_cycle_regime(phase: str) -> str:
    phase = (phase or "").lower()
    if phase in DANGEROUS_PHASES:
        return "danger"
    if phase in CAUTION_PHASES:
        return "caution"
    if phase in BULL_PHASES:
        return "bull"
    if phase in BEAR_PHASES:
        return "bear"
    return "unknown"


def compute_cycle_engine(data_dir: Path) -> Dict[str, Any]:
    """
    Construit la vision "Cycle Engine Pro" à partir de momentum_scores.json.

    Source attendue : data/analysis/momentum_scores.json
    Format : liste de dicts avec au moins :
      - symbol
      - components.cycle_phase
      - components.cycle_phase_score
      - meta_score (ou components.meta_score)
    """

    momentum_path = data_dir / "analysis" / "momentum_scores.json"
    raw: Any = load_json_file(str(momentum_path), default=[])

    if not isinstance(raw, list):
        logger.warning(
            "[cycle_engine_pro] momentum_scores.json n'est pas une liste (type=%s), "
            "aucun asset ne sera traité.",
            type(raw),
        )
        assets_src: List[Dict[str, Any]] = []
    else:
        assets_src = raw

    assets: List[Dict[str, Any]] = []
    by_phase: Dict[str, int] = {}
    by_regime: Dict[str, int] = {
        "bull": 0,
        "bear": 0,
        "caution": 0,
        "danger": 0,
        "unknown": 0,
    }

    total_score = 0.0
    nb_with_score = 0

    for row in assets_src:
        symbol = row.get("symbol")
        comps = row.get("components", {}) or {}
        cycle_phase = comps.get("cycle_phase") or row.get("cycle_phase") or "unknown"
        cycle_phase_score = (
            comps.get("cycle_phase_score")
            if comps.get("cycle_phase_score") is not None
            else row.get("cycle_phase_score")
        )
        meta_score = (
            row.get("meta_score")
            if row.get("meta_score") is not None
            else comps.get("meta_score")
        )

        regime = _classify_cycle_regime(cycle_phase)

        by_phase[cycle_phase] = by_phase.get(cycle_phase, 0) + 1
        by_regime[regime] = by_regime.get(regime, 0) + 1

        if isinstance(cycle_phase_score, (int, float)):
            total_score += float(cycle_phase_score)
            nb_with_score += 1

        assets.append(
            {
                "symbol": symbol,
                "cycle_phase": cycle_phase,
                "cycle_phase_score": cycle_phase_score,
                "cycle_regime": regime,
                "meta_score": meta_score,
            }
        )

    nb_assets = len(assets)

    avg_cycle_score = total_score / nb_with_score if nb_with_score > 0 else 0.0

    # Déterminer un flag global simple
    nb_danger = by_regime.get("danger", 0)
    nb_caution = by_regime.get("caution", 0)

    if nb_danger > 0:
        global_flag = "danger"
    elif nb_caution > 0:
        global_flag = "caution"
    else:
        global_flag = "ok"

    stats: Dict[str, Any] = {
        "nb_assets": nb_assets,
        "by_phase": by_phase,
        "by_regime": by_regime,
        "avg_cycle_score": avg_cycle_score,
        "global_flag": global_flag,
    }

    logger.info(
        "[cycle_engine_pro] Cycle analysé pour %d assets (global_flag=%s).",
        nb_assets,
        global_flag,
    )

    return {
        "stats": stats,
        "assets": assets,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    root_dir, data_dir = get_paths()
    logger.info(
        "[cycle_engine_pro] ROOT_DIR=%s, DATA_DIR=%s",
        root_dir,
        data_dir,
    )

    overview = compute_cycle_engine(data_dir)
    out_path = data_dir / "analysis" / "cycle_engine_pro.json"
    save_json_file(str(out_path), overview)
    logger.info(
        "[cycle_engine_pro] cycle_engine_pro.json sauvegardé (%s, assets=%d).",
        out_path,
        overview.get("stats", {}).get("nb_assets", 0),
    )


if __name__ == "__main__":
    main()
