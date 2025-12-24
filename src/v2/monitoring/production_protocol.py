import logging
import os
from datetime import datetime, timezone

from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = logging.getLogger(__name__)


def _get_env() -> str:
    """
    Retourne l'env logique NSC : PROD / PREPROD / DEV.
    Par défaut on considère PREPROD (plus safe pour l’instant).
    """
    env = os.getenv("NSC_ENV") or os.getenv("ENV") or "PREPROD"
    return env.upper()


def main() -> None:
    env = _get_env()

    # get_data_dir() dans ta base ne prend pas de kwargs, on l’utilise tel quel
    data_dir = get_data_dir()
    telemetry_dir = os.path.join(data_dir, "telemetry")
    analysis_dir = os.path.join(data_dir, "analysis")

    os.makedirs(telemetry_dir, exist_ok=True)
    os.makedirs(analysis_dir, exist_ok=True)

    # === Chargement des sources ===
    system_metrics = load_json_file(
        os.path.join(telemetry_dir, "system_metrics.json"),
        default={},
    )

    logs_overview = load_json_file(
        os.path.join(analysis_dir, "logs_overview_light.json"),
        default={"has_errors": False, "steps_error": 0, "signals": {}},
    )

    backpressure_state = load_json_file(
        os.path.join(telemetry_dir, "backpressure_state.json"),
        default={"mode": "normal", "reasons": []},
    )

    stress_state = load_json_file(
        os.path.join(telemetry_dir, "stress_test_engine.json"),
        default={"global_flag": "ok", "nb_breaches": 0, "worst_drawdown_pct": 0.0},
    )

    orchestrator_state = load_json_file(
        os.path.join(telemetry_dir, "orchestrator_state.json"),
        default={"mode": "normal", "backpressure_flag": "ok", "nb_recent_errors": None},
    )

    # === Checks logiques ===
    logs_clean = not logs_overview.get("has_errors", False) and logs_overview.get(
        "steps_error", 0
    ) == 0

    backpressure_mode = backpressure_state.get("mode", "normal")
    # On considère "normal" et "safe" comme OK
    backpressure_ok = backpressure_mode in ("normal", "safe")

    stress_flag = str(stress_state.get("global_flag", "ok")).lower()
    # "ok" ou "warning" => OK ; "critical" => pas OK
    stress_ok = stress_flag in ("ok", "warning")

    checks = {
        "telemetry_ok": True,  # on considère OK tant qu'on lit les fichiers
        "logs_clean": logs_clean,
        "backpressure_ok": backpressure_ok,
        "stress_ok": stress_ok,
    }

    reasons: list[str] = []

    if not stress_ok:
        reasons.append("Stress Test Engine en mode CRITICAL (ou nb_breaches >= 3).")

    if not backpressure_ok:
        reasons.append("Backpressure Engine actif : ok.")

    # === Détermination du mode en fonction de l'env ===
    if env == "PROD":
        # En production réelle : strict
        if reasons:
            mode = "emergency"
        else:
            mode = "normal"
    else:
        # PREPROD / DEV : on ne met plus jamais "emergency" à cause des stress tests / backpressure
        if reasons:
            mode = "preprod_warning"
        else:
            mode = "normal"

    # === Gouvernance (placeholder pour la suite) ===
    governance = {
        "kill_switch_status": system_metrics.get("kill_switch_status"),
        "kill_switch_reason": system_metrics.get("kill_switch_reason"),
        "governance_flag": system_metrics.get("governance_flag"),
        "governance_score": system_metrics.get("governance_score"),
    }

    sources = {
        "system_metrics": system_metrics,
        "orchestrator_state": {
            "mode": orchestrator_state.get("mode"),
            "backpressure_flag": orchestrator_state.get("backpressure_flag"),
            "nb_recent_errors": orchestrator_state.get("nb_recent_errors"),
        },
        "logs_overview_light": logs_overview,
        "stress_test_engine": stress_state,
    }

    # === Recommandations ===
    recommendations: list[str] = []
    if env == "PROD" and mode == "emergency":
        recommendations = [
            "Activer/maintenir le kill-switch global et arrêter toute exécution réelle.",
            "Analyser les erreurs critiques dans logs_overview_light.json et les logs détaillés.",
            "Revoir le sizing, les limites de drawdown et le Stress Test Engine avant toute reprise.",
        ]
    elif env != "PROD" and reasons:
        recommendations = [
            "Préprod/Dev : analyser les stress tests et le backpressure avant d'activer le mode réel.",
        ]

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "reasons": reasons,
        "sources": sources,
        "checks": checks,
        "governance": governance,
        "recommendations": recommendations,
    }

    out_path = os.path.join(telemetry_dir, "production_protocol.json")
    save_json_file(out_path, payload)
    logger.info(
        "[production_protocol] production_protocol.json sauvegardé (%s, reasons=%s, env=%s)",
        mode,
        "; ".join(reasons) if reasons else "aucune",
        env,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
