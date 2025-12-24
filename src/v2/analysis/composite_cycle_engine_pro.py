# src/v2/analysis/composite_cycle_engine_pro.py

from __future__ import annotations

import os
import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Logger centralisé avec fallback
try:
    from src.v2.logger import get_logger  # wrapper central si présent
except ModuleNotFoundError:  # fallback vers l'ancien chemin
    from src.v2.utils.logger import get_logger  # type: ignore

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


# === Helpers locaux pour ne plus dépendre de src.v2.utils.env =================


def get_data_dir() -> Path:
    """
    Retourne le répertoire DATA de NSC.

    - Si NSC_DATA_DIR est défini: on l'utilise.
    - Sinon: on part du répertoire courant (cd /opt/nsc/app → ./data).
    """
    env_dir = os.environ.get("NSC_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    # Hypothèse standard NSC: on lance les modules depuis /opt/nsc/app
    return Path("data").resolve()


def get_env(default: str = "PREPROD") -> str:
    """
    Retourne l'environnement NSC (PREPROD / PROD / etc.).
    """
    return os.environ.get("NSC_ENV", default)


# === Petits utilitaires internes =============================================


def _now_utc_iso() -> str:
    """Retourne un timestamp UTC ISO8601 (sans microsecondes, suffixé par 'Z')."""
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def _normalize_score(raw: Optional[float]) -> float:
    """
    Normalise un score en [0, 100].
    - Si None -> 50 (neutre)
    - Si déjà entre 0 et 100 -> inchangé
    - Si entre 0 et 1 -> multiplié par 100
    - Clamp entre 0 et 100
    """
    if raw is None:
        return 50.0

    try:
        val = float(raw)
    except (TypeError, ValueError):
        return 50.0

    # Si c'est un score 0–1, on le passe en 0–100
    if 0.0 <= val <= 1.0:
        val *= 100.0

    if val < 0.0:
        val = 0.0
    if val > 100.0:
        val = 100.0

    return round(val, 2)


def _flag_from_score(score: float) -> str:
    """
    Traduit un score de cycle en flag global.
    - >= 70 : 'ok' (conditions favorables ou cycles alignés)
    - 40–70 : 'caution' (conditions intermédiaires / mixtes)
    - < 40  : 'stress' (conditions défavorables)
    """
    if score >= 70.0:
        return "ok"
    if score >= 40.0:
        return "caution"
    return "stress"


def _severity_from_flag(flag: str) -> str:
    """Mappe le flag global vers une sévérité d’event bus."""
    mapping = {
        "ok": "info",
        "caution": "warning",
        "stress": "critical",
    }
    return mapping.get(flag, "info")


def _extract_cycle_info(
    cycle_data: Dict[str, Any]
) -> Tuple[float, str, Dict[str, Any], list[str]]:
    """
    Extrait un score et un 'regime' à partir d'un éventuel moteur de cycle existant.
    On essaye d'être robuste aux variations de format :
    - composite_score / score / cycle_score
    - phase / regime
    - flags éventuels
    """
    reasons: list[str] = []
    metrics: Dict[str, Any] = {}

    if not cycle_data:
        reasons.append(
            "Aucun fichier de cycle disponible (cycle_engine_pro.json introuvable ou vide)."
        )
        return 50.0, "unknown", metrics, reasons

    # Score primaire
    raw_score = (
        cycle_data.get("composite_score")
        or cycle_data.get("score")
        or cycle_data.get("cycle_score")
    )
    score = _normalize_score(raw_score)

    # Phase / régime s'ils existent
    regime = cycle_data.get("regime") or cycle_data.get("phase") or "unknown"

    # On capture quelques champs utiles s'ils sont présents
    for key in [
        "short_term_phase",
        "intermediate_term_phase",
        "long_term_phase",
        "dominant_cycle",
        "cycle_confidence",
        "cycle_volatility",
    ]:
        if key in cycle_data:
            metrics[key] = cycle_data[key]

    # Raison textuelle de base
    if raw_score is None:
        reasons.append("Score de cycle absent – utilisation d'un score neutre (50).")
    else:
        reasons.append(
            f"Score de cycle brut détecté: {raw_score} → normalisé à {score:.2f}."
        )

    # Si un flag ou un commentaire existe déjà, on le remonte
    existing_flag = cycle_data.get("global_flag") or cycle_data.get("flag")
    if existing_flag:
        reasons.append(f"Flag de cycle existant: {existing_flag}.")

    existing_reasons = cycle_data.get("reasons")
    if isinstance(existing_reasons, list):
        reasons.extend([str(r) for r in existing_reasons])

    return score, regime, metrics, reasons


def build_composite_cycle_state(
    data_dir: Path,
    env: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Construit l'état composite de cycle à partir :
    - du moteur de cycle principal (cycle_engine_pro.json) si disponible
    - éventuellement d'autres signaux de cycle à venir (placeholder)
    """
    analysis_dir = data_dir / "analysis"
    cycle_file = analysis_dir / "cycle_engine_pro.json"

    # Lecture robuste du moteur de cycle existant
    cycle_data = load_json_file(cycle_file, default={})
    score, regime, extra_metrics, reasons = _extract_cycle_info(cycle_data)

    global_flag = _flag_from_score(score)
    severity = _severity_from_flag(global_flag)

    state: Dict[str, Any] = {
        "timestamp": _now_utc_iso(),
        "env": env,
        "symbol": "global",  # Composite global par défaut
        "regime": regime,
        "global_flag": global_flag,
        "score": score,
        "metrics": extra_metrics,
        "reasons": reasons,
    }

    logger.info(
        "[composite_cycle_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f",
        env,
        regime,
        global_flag,
        score,
    )

    return state, severity


def main() -> None:
    data_dir = get_data_dir()
    env = get_env(default="PREPROD")

    logger.info(
        "[composite_cycle_engine_pro] DATA_DIR=%s, env=%s",
        data_dir,
        env,
    )

    state, severity = build_composite_cycle_state(data_dir=data_dir, env=env)

    # Sauvegarde JSON
    output_path = data_dir / "analysis" / "composite_cycle_engine_pro.json"
    save_json_file(output_path, state)
    logger.info(
        "[composite_cycle_engine_pro] composite_cycle_engine_pro.json sauvegardé "
        "(regime=%s, global_flag=%s, score=%.2f)",
        state.get("regime"),
        state.get("global_flag"),
        state.get("score"),
    )

    # Publication dans l'event bus
    try:
        publish_event(
            event_type="cycle.composite.state",
            source="composite_cycle_engine_pro",
            severity=severity,
            payload=state,
        )
        logger.info(
            "[composite_cycle_engine_pro] Event cycle.composite.state publié "
            "(severity=%s, score=%.2f)",
            severity,
            state.get("score"),
        )
    except Exception as e:  # pragma: no cover – robustesse runtime
        logger.error(
            "[composite_cycle_engine_pro] Impossible de publier l'event "
            "cycle.composite.state : %s",
            e,
        )


if __name__ == "__main__":
    main()
