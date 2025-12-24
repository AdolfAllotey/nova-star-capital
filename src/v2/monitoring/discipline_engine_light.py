import os
from datetime import datetime, timezone

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file

logger = get_logger(__name__)


def _compute_discipline_score(logs_overview: dict, production_protocol: dict) -> dict:
    """
    Calcule un score de discipline simple à partir des infos disponibles.
    Score de base = 80, on dégrade selon les erreurs / modes d'urgence.
    """
    score = 80.0
    reasons = []

    # 1) Analyse des erreurs de logs (logs_overview_light.json)
    # On essaie plusieurs clés possibles, tout est optionnel.
    error_keys = ["errors", "nb_errors", "steps_error"]
    total_errors = 0

    for key in error_keys:
        value = logs_overview.get(key, 0)
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 0
        total_errors += max(value, 0)

    if total_errors > 0:
        # On dégrade la discipline si des erreurs sont détectées dans les logs
        score -= min(30.0, 5.0 * total_errors)
        reasons.append(f"{total_errors} erreur(s) détectée(s) dans logs_overview_light.")

    # 2) Mode global de production (production_protocol.json)
    mode = production_protocol.get("mode") or production_protocol.get("global_mode")
    if mode:
        mode = str(mode).lower()
        if mode in {"emergency", "critical"}:
            score -= 30.0
            reasons.append(f"Mode production '{mode}' (emergency/critical).")
        elif mode in {"degraded", "warning"}:
            score -= 15.0
            reasons.append(f"Mode production '{mode}' (degraded/warning).")

    # Clamp
    score = max(0.0, min(100.0, score))

    # Flag
    if score >= 70.0:
        flag = "ok"
    elif score >= 40.0:
        flag = "warning"
    else:
        flag = "critical"

    return {
        "score": round(score, 2),
        "flag": flag,
        "reasons": reasons,
        "mode": mode or "unknown",
        "total_errors": total_errors,
    }


def main() -> None:
    data_dir = get_data_dir()
    analysis_dir = os.path.join(data_dir, "analysis")
    telemetry_dir = os.path.join(data_dir, "telemetry")
    os.makedirs(analysis_dir, exist_ok=True)
    os.makedirs(telemetry_dir, exist_ok=True)

    logger.info("[discipline_engine_light] DATA_DIR=%s", data_dir)

    # On lit les fichiers de télémétrie si présents, sinon {} grâce au default
    logs_overview_path = os.path.join(analysis_dir, "logs_overview_light.json")
    production_protocol_path = os.path.join(telemetry_dir, "production_protocol.json")

    logs_overview = load_json_file(logs_overview_path, default={})
    production_protocol = load_json_file(production_protocol_path, default={})

    metrics = _compute_discipline_score(logs_overview, production_protocol)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine": "discipline_engine_light",
        "score": metrics["score"],
        "flag": metrics["flag"],
        "details": {
            "mode": metrics["mode"],
            "total_errors": metrics["total_errors"],
            "reasons": metrics["reasons"],
        },
    }

    out_path = os.path.join(analysis_dir, "discipline_engine_light.json")
    save_json_file(out_path, payload)
    logger.info(
        "[discipline_engine_light] discipline_engine_light.json sauvegardé (%s, score=%.2f, flag=%s)",
        out_path,
        metrics["score"],
        metrics["flag"],
    )


if __name__ == "__main__":
    main()
