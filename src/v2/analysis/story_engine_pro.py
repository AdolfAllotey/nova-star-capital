"""
Story Engine Pro – Saison 2
Analyse la "force de la narrative" par asset à partir de momentum_scores.json.

Entrée principale :
- data/analysis/momentum_scores.json  (output du momentum_scoring)

Sortie :
- data/analysis/story_engine_pro.json

Structure de sortie :
{
  "generated_at": "...",
  "stats": {
    "nb_assets": ...,
    "by_regime": {
      "strong_story": ...,
      "healthy_story": ...,
      "weak_story": ...,
      "no_story": ...
    },
    "nb_overhyped": ...,
    "nb_underhyped": ...,
    "global_flag": "ok" | "caution" | "danger" | "unknown"
  },
  "assets": [
    {
      "symbol": "bitcoin",
      "story_strength": 65.2,
      "meta_score": 58.7,
      "momentum_score": 72.1,
      "sentiment_score": 55.0,
      "story_regime": "healthy_story",
      "price_vs_story": "aligned_or_noise" |
                        "story_strong_price_lagging" |
                        "price_strong_story_weak",
      "reasons": [...],
      "flags": {
        "story_ok": true,
        "overhyped": false,
        "underhyped": false,
        "hard_veto": false,
        "soft_veto": false
      }
    },
    ...
  ]
}
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("story_engine_pro")


# ---------------------------------------------------------------------------
# Helpers ROOT/DATA
# ---------------------------------------------------------------------------


def _get_root_and_data_dir() -> Tuple[Path, Path]:
    """
    Détermine ROOT_DIR et DATA_DIR de manière robuste :
    - NSC_ROOT_DIR / NSC_DATA_DIR si définis
    - sinon, remonte à la racine du projet depuis ce fichier.
    """
    root_env = os.getenv("NSC_ROOT_DIR")
    data_env = os.getenv("NSC_DATA_DIR")

    if root_env:
        root = Path(root_env).resolve()
    else:
        # .../src/v2/analysis/story_engine_pro.py → remonte 3 niveaux → projet
        root = Path(__file__).resolve().parents[3]

    if data_env:
        data = Path(data_env).resolve()
    else:
        data = root / "data"

    return root, data


# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------


def _load_momentum_scores(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Charge momentum_scores.json dans data/analysis/.
    Gère à la fois :
    - un tableau direct [ {...}, {...} ]
    - un dict {"assets": [ ... ]}
    """
    path = data_dir / "analysis" / "momentum_scores.json"
    raw = load_json_file(path, default=[])

    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        assets = raw.get("assets")
        if isinstance(assets, list):
            return assets

    return []


# ---------------------------------------------------------------------------
# Scoring "narrative" par asset
# ---------------------------------------------------------------------------


def _compute_story_for_asset(row: Dict[str, Any]) -> Dict[str, Any]:
    symbol = (
        row.get("symbol")
        or row.get("asset")
        or row.get("token")
        or "unknown"
    )

    components = row.get("components") or {}
    filters = row.get("filters") or {}

    # On s'appuie sur ce qu'on connaît déjà de momentum_scores.json
    meta_score = float(
        row.get("meta_score")
        or components.get("meta_score")
        or 0.0
    )
    momentum = float(components.get("momentum") or 0.0)
    sentiment_comp = float(components.get("sentiment") or 50.0)

    # Score "story" = blend meta + momentum + sentiment
    story_strength = 0.5 * meta_score + 0.3 * momentum + 0.2 * sentiment_comp
    story_strength = max(0.0, min(100.0, story_strength))

    price_ok = bool(filters.get("price_action_ok", True))
    micro_ok = bool(filters.get("micro_ok", True))
    orderflow_ok = bool(filters.get("orderflow_ok", True))

    # Relation prix vs narrative
    if story_strength >= 75 and not price_ok:
        price_vs_story = "story_strong_price_lagging"
    elif story_strength <= 45 and price_ok:
        price_vs_story = "price_strong_story_weak"
    else:
        price_vs_story = "aligned_or_noise"

    # Régime de narrative
    if story_strength >= 80:
        story_regime = "strong_story"
    elif story_strength >= 60:
        story_regime = "healthy_story"
    elif story_strength >= 45:
        story_regime = "weak_story"
    else:
        story_regime = "no_story"

    reasons: List[str] = []

    # Commentaire principal sur la force de la story
    if story_regime == "strong_story":
        reasons.append("Narrative très forte et cohérente (Story Engine Pro).")
    elif story_regime == "healthy_story":
        reasons.append("Narrative solide / cohérente.")
    elif story_regime == "weak_story":
        reasons.append("Narrative présente mais fragile.")
    else:
        reasons.append("Pas de narrative claire pour l'instant.")

    # Commentaire sur la relation prix / story
    if price_vs_story == "story_strong_price_lagging":
        reasons.append("Prix en retard sur la narrative (potentiel rattrapage).")
    elif price_vs_story == "price_strong_story_weak":
        reasons.append("Prix fort mais narrative faible (attention au bull trap).")

    # Flags "overhyped / underhyped" simplifiés
    overhyped = story_strength >= 70 and not micro_ok
    underhyped = story_strength >= 60 and (not orderflow_ok or not price_ok)

    flags = {
        "story_ok": story_regime in ("strong_story", "healthy_story"),
        "overhyped": overhyped,
        "underhyped": underhyped,
        "hard_veto": False,
        "soft_veto": story_regime in ("weak_story", "no_story"),
    }

    return {
        "symbol": symbol,
        "story_strength": round(story_strength, 2),
        "meta_score": round(meta_score, 2),
        "momentum_score": round(momentum, 2),
        "sentiment_score": round(sentiment_comp, 2),
        "story_regime": story_regime,
        "price_vs_story": price_vs_story,
        "reasons": reasons,
        "flags": flags,
    }


# ---------------------------------------------------------------------------
# Agrégation globale
# ---------------------------------------------------------------------------


def compute_story_overview(data_dir: Path) -> Dict[str, Any]:
    momentum_rows = _load_momentum_scores(data_dir)

    assets: List[Dict[str, Any]] = []
    for row in momentum_rows:
        try:
            assets.append(_compute_story_for_asset(row))
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "[story_engine_pro] Erreur sur asset %s: %s",
                row.get("symbol") or row.get("asset") or "unknown",
                exc,
            )

    nb_assets = len(assets)
    by_regime = {
        "strong_story": 0,
        "healthy_story": 0,
        "weak_story": 0,
        "no_story": 0,
    }
    nb_overhyped = 0
    nb_underhyped = 0

    for a in assets:
        reg = a.get("story_regime", "no_story")
        if reg in by_regime:
            by_regime[reg] += 1

        fl = a.get("flags") or {}
        if fl.get("overhyped"):
            nb_overhyped += 1
        if fl.get("underhyped"):
            nb_underhyped += 1

    nb_good = by_regime["strong_story"] + by_regime["healthy_story"]
    nb_bad = by_regime["no_story"]

    if nb_assets == 0:
        global_flag = "unknown"
    elif nb_good >= max(1, nb_assets // 2):
        global_flag = "ok"
    elif nb_bad > 0 or nb_underhyped > 0:
        global_flag = "caution"
    else:
        global_flag = "caution"

    stats = {
        "nb_assets": nb_assets,
        "by_regime": by_regime,
        "nb_overhyped": nb_overhyped,
        "nb_underhyped": nb_underhyped,
        "global_flag": global_flag,
    }

    overview: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "assets": assets,
    }
    return overview


# ---------------------------------------------------------------------------
# Entrée CLI
# ---------------------------------------------------------------------------


def main() -> None:
    root_dir, data_dir = _get_root_and_data_dir()
    logger.info(
        "[story_engine_pro] ROOT_DIR=%s, DATA_DIR=%s",
        root_dir,
        data_dir,
    )

    overview = compute_story_overview(data_dir)
    stats = overview.get("stats", {})

    logger.info(
        "[story_engine_pro] Story Engine Pro calculé pour %d assets (global_flag=%s).",
        stats.get("nb_assets", 0),
        stats.get("global_flag", "unknown"),
    )

    out_path = data_dir / "analysis" / "story_engine_pro.json"
    save_json_file(out_path, overview)
    logger.info(
        "[story_engine_pro] story_engine_pro.json sauvegardé (%s, assets=%d).",
        out_path,
        stats.get("nb_assets", 0),
    )


if __name__ == "__main__":
    main()
