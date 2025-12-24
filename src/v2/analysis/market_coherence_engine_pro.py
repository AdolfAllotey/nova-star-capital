"""
market_coherence_engine_pro.py

Market Coherence Engine PRO
---------------------------

Objectif :
- Mesurer à quel point les différents moteurs de haut niveau (corrélation, dispersion,
  migration de liquidité, volatilité, stabilité, etc.) "racontent la même histoire".
- Produire un score de cohérence global (0–100), un regime, un global_flag et une
  liste de raisons lisibles dans l’interface NSC / consoles.

Comportement si aucune donnée :
- Ne plante jamais.
- Renvoie un score neutre (50), regime="unknown", global_flag="caution".
- Publie un event "market.coherence.state" en severity="warning".
"""

from __future__ import annotations

import os
import datetime as dt
import logging
from pathlib import Path
from typing import Any, Dict, Tuple, List

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.core.message_bus import publish_event

logger = logging.getLogger(__name__)

NEUTRAL_SCORE = 50.0


# ---------------------------------------------------------------------------
# Helpers locaux pour DATA_DIR et ENV (évite la dépendance à src.v2.utils.env)
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """
    Retourne le répertoire data de NSC.

    - Lit la variable d'environnement NSC_DATA_DIR si présente.
    - Sinon, utilise 'data' relatif à la racine du projet.
    """
    root = Path(__file__).resolve().parents[3]  # .../opt/nsc/app
    default_data = root / "data"
    env_path = os.getenv("NSC_DATA_DIR")
    if env_path:
        return Path(env_path).resolve()
    return default_data


def get_env() -> str:
    """
    Retourne l'environnement courant (DEV / PREPROD / PROD, etc.).

    - Lit NSC_ENV si défini.
    - Par défaut : PREPROD (cohérent avec le reste de la stack).
    """
    return os.getenv("NSC_ENV", "PREPROD")


# ---------------------------------------------------------------------------
# Cœur du moteur
# ---------------------------------------------------------------------------

def _now_iso_utc() -> str:
    """Retourne un timestamp ISO8601 en UTC (suffixe Z)."""
    # On garde utcnow() pour rester aligné avec les autres moteurs PRO
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def build_market_coherence_state(
    data_dir: Path,
    env: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état de cohérence de marché à partir d'un fichier
    `market_coherence_components.json` (facultatif).

    Fichier attendu (optionnel) :
    data/analysis/market_coherence_components.json

    Format conseillé (mais pas obligatoire, le moteur est robuste) :
    {
      "score": 72.5,
      "regime": "coherent" | "incoherent" | "neutral",
      "global_flag": "risk_on" | "risk_off" | "caution",
      "nb_engines": 8,
      "nb_confirming": 6,
      "nb_conflicting": 2,
      "agreement_ratio": 0.75,
      "disagreement_ratio": 0.25
    }
    """

    components_path = data_dir / "analysis" / "market_coherence_components.json"
    raw: Any = load_json_file(components_path, default={})

    reasons: List[str] = []
    severity = "info"

    if not raw or not isinstance(raw, dict):
        # Aucun signal exploitable → neutre, mais on log en warning pour l’observabilité.
        logger.info(
            "[market_coherence_engine_pro] Aucune donnée de cohérence détectée – utilisation du score neutre."
        )
        severity = "warning"

        state: Dict[str, Any] = {
            "timestamp": _now_iso_utc(),
            "env": env,
            "symbol": "global",
            "regime": "unknown",
            "global_flag": "caution",
            "score": NEUTRAL_SCORE,
            "metrics": {
                "nb_engines": 0,
                "nb_confirming": 0,
                "nb_conflicting": 0,
                "agreement_ratio": None,
                "disagreement_ratio": None,
            },
            "reasons": [
                "Aucune donnée de cohérence de marché exploitable – score neutre."
            ],
        }
        return state, severity

    # Lecture robuste des champs éventuels
    score_raw = raw.get("score", NEUTRAL_SCORE)
    try:
        score = float(score_raw)
    except (TypeError, ValueError):
        score = NEUTRAL_SCORE
        reasons.append(
            "Score invalide dans les données brutes – utilisation du score neutre (50)."
        )

    nb_engines = raw.get("nb_engines")
    nb_confirming = raw.get("nb_confirming")
    nb_conflicting = raw.get("nb_conflicting")
    agreement_ratio = raw.get("agreement_ratio")
    disagreement_ratio = raw.get("disagreement_ratio")

    # Détermination du regime / flag si non fournis
    regime = raw.get("regime")
    global_flag = raw.get("global_flag")

    if regime is None:
        if score >= 70:
            regime = "coherent"
        elif score <= 30:
            regime = "incoherent"
        else:
            regime = "neutral"

    if global_flag is None:
        if regime == "coherent" and score >= 70:
            global_flag = "risk_on"
        elif regime == "incoherent" and score <= 30:
            global_flag = "caution"
        else:
            global_flag = "caution"

    # Déterminer la sévérité de l’event
    if regime == "incoherent" and score <= 30:
        severity = "warning"
        reasons.append(
            "Signaux de fond peu cohérents entre eux – prudence recommandée."
        )
    elif regime == "coherent" and score >= 70:
        severity = "info"
        reasons.append(
            "Signaux de fond globalement alignés – cohérence élevée."
        )
    else:
        severity = "info"
        reasons.append("Cohérence de marché modérée ou incertaine – lecture neutre.")

    logger.info(
        "[market_coherence_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f, nb_engines=%s",
        env,
        regime,
        global_flag,
        score,
        nb_engines,
    )

    state = {
        "timestamp": _now_iso_utc(),
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": round(score, 2),
        "metrics": {
            "nb_engines": nb_engines,
            "nb_confirming": nb_confirming,
            "nb_conflicting": nb_conflicting,
            "agreement_ratio": agreement_ratio,
            "disagreement_ratio": disagreement_ratio,
        },
        "reasons": reasons,
    }

    return state, severity


def main() -> None:
    data_dir: Path = get_data_dir()
    env: str = get_env()

    logger.info(
        "[market_coherence_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_market_coherence_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    out_path = data_dir / "analysis" / "market_coherence_engine_pro.json"
    save_json_file(out_path, state)
    logger.info(
        "[market_coherence_engine_pro] market_coherence_engine_pro.json sauvegardé (regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication dans le message bus
    publish_event(
        "market.coherence.state",
        "market_coherence_engine_pro",
        state,
        severity=severity,
    )
    logger.info(
        "[market_coherence_engine_pro] Event market.coherence.state publié (severity=%s, score=%.2f)",
        severity,
        state.get("score"),
    )


if __name__ == "__main__":
    main()
