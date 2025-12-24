# src/v2/analysis/system_metrics_pro.py

import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)


def _as_list(obj: Any) -> List[dict]:
    """
    Normalise un contenu JSON en liste de dicts.
    Accepte : liste, dict avec clé 'data' ou 'signals' ou 'items'.
    """
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("signals", "data", "items"):
            if key in obj and isinstance(obj[key], list):
                return obj[key]
    return []


def compute_and_save_system_metrics(
    data_dir: str,
    env: str | None = None,
    step_timings: Dict[str, float] | None = None,
    step_status: Dict[str, str] | None = None,
) -> None:
    """
    Agrège les métriques système & trading et sauvegarde :
    - telemetry/system_metrics.json
    - analysis/logs_overview_light.json (utilisé par governance_engine_pro)
    """

    env = env or os.getenv("NSC_ENV", "PREPROD")
    step_timings = step_timings or {}
    step_status = step_status or {}

    logger.info(
        "[system_metrics_pro] Calcul des métriques système: data_dir=%s, env=%s",
        data_dir,
        env,
    )

    # --- Lecture des fichiers clés ---

    sized_signals = load_json_file(
        os.path.join(data_dir, "trading", "sized_signals.json"),
        default=[],
    )
    execution_attempts = load_json_file(
        os.path.join(data_dir, "trading", "execution_attempts.json"),
        default=[],
    )
    simulated_fills = load_json_file(
        os.path.join(data_dir, "trading", "simulated_fills.json"),
        default=[],
    )
    open_positions = load_json_file(
        os.path.join(data_dir, "trading", "open_positions.json"),
        default=[],
    )
    risk_limits = load_json_file(
        os.path.join(data_dir, "trading", "risk_limits.json"),
        default={},
    )
    kill_switch = load_json_file(
        os.path.join(data_dir, "trading", "kill_switch.json"),
        default={},
    )
    gov = load_json_file(
        os.path.join(data_dir, "analysis", "governance_engine_pro.json"),
        default={},
    )

    sized_signals_list = _as_list(sized_signals)
    execution_attempts_list = _as_list(execution_attempts)
    simulated_fills_list = _as_list(simulated_fills)
    open_positions_list = _as_list(open_positions)

    nb_sized = len(sized_signals_list)
    nb_exec_attempts = len(execution_attempts_list)
    nb_fills = len(simulated_fills_list)
    nb_open_positions = len(open_positions_list)

    risk_mode = risk_limits.get("mode")
    risk_on_off = risk_limits.get("risk_on_off")
    size_factor = risk_limits.get("size_factor")
    max_positions = risk_limits.get("max_positions")

    kill_status = kill_switch.get("global_status") or kill_switch.get("status")
    kill_reason = kill_switch.get("reason")

    gov_flag = gov.get("flag")
    gov_score = gov.get("score")

    # --- Synthèse steps / timings ---

    all_step_names = sorted(set(step_timings.keys()) | set(step_status.keys()))
    steps_metrics = []
    nb_steps_ok = 0
    nb_steps_error = 0

    for name in all_step_names:
        status = step_status.get(name, "unknown")
        if status == "ok":
            nb_steps_ok += 1
        elif status == "error":
            nb_steps_error += 1

        steps_metrics.append(
            {
                "name": name,
                "status": status,
                "duration_sec": step_timings.get(name),
            }
        )

    total_duration = sum(d for d in step_timings.values() if d is not None)

    # --- Construction de system_metrics.json ---

    now_utc = datetime.now(timezone.utc).isoformat()

    system_metrics: Dict[str, Any] = {
        "timestamp": now_utc,
        "env": env,
        "steps": steps_metrics,
        "summary": {
            "total_duration_sec": total_duration,
            "nb_steps_ok": nb_steps_ok,
            "nb_steps_error": nb_steps_error,
            "nb_signals_sized": nb_sized,
            "nb_execution_attempts": nb_exec_attempts,
            "nb_fills": nb_fills,
            "nb_open_positions": nb_open_positions,
            "risk_mode": risk_mode,
            "risk_on_off": risk_on_off,
            "risk_size_factor": size_factor,
            "risk_max_positions": max_positions,
            "kill_switch_status": kill_status,
            "kill_switch_reason": kill_reason,
            "governance_flag": gov_flag,
            "governance_score": gov_score,
        },
        "signals": {
            "sized_signals": nb_sized,
            "execution_attempts": nb_exec_attempts,
            "fills": nb_fills,
            "open_positions": nb_open_positions,
        },
        "risk": {
            "limits": {
                "mode": risk_mode,
                "risk_on_off": risk_on_off,
                "size_factor": size_factor,
                "max_positions": max_positions,
            },
            "kill_switch": {
                "status": kill_status,
                "reason": kill_reason,
            },
        },
        "governance": {
            "flag": gov_flag,
            "score": gov_score,
        },
    }

    telemetry_dir = os.path.join(data_dir, "telemetry")
    os.makedirs(telemetry_dir, exist_ok=True)
    system_metrics_path = os.path.join(telemetry_dir, "system_metrics.json")
    save_json_file(system_metrics_path, system_metrics)
    logger.info(
        "[system_metrics_pro] system_metrics.json sauvegardé (%s)",
        system_metrics_path,
    )

    # --- logs_overview_light.json pour Governance Engine Pro ---

    logs_overview_light: Dict[str, Any] = {
        "timestamp": now_utc,
        "env": env,
        "has_errors": nb_steps_error > 0,
        "nb_errors": nb_steps_error,
        "steps_error": [s["name"] for s in steps_metrics if s["status"] == "error"],
        "steps": steps_metrics,
        "signals": {
            "nb_sized": nb_sized,
            "nb_exec_attempts": nb_exec_attempts,
            "nb_fills": nb_fills,
            "nb_open_positions": nb_open_positions,
        },
        "risk": {
            "mode": risk_mode,
            "risk_on_off": risk_on_off,
            "size_factor": size_factor,
            "max_positions": max_positions,
            "kill_switch_status": kill_status,
            "kill_switch_reason": kill_reason,
        },
        "governance": {
            "flag": gov_flag,
            "score": gov_score,
        },
    }

    analysis_dir = os.path.join(data_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    logs_overview_path = os.path.join(analysis_dir, "logs_overview_light.json")
    save_json_file(logs_overview_path, logs_overview_light)
    logger.info(
        "[system_metrics_pro] logs_overview_light.json sauvegardé (%s)",
        logs_overview_path,
    )


def main() -> None:
    root_dir = os.getenv("NSC_ROOT_DIR", os.getcwd())
    data_dir = os.getenv("NSC_DATA_DIR", os.path.join(root_dir, "data"))
    env = os.getenv("NSC_ENV", "PREPROD")

    logger.info(
        "[system_metrics_pro] Lancement en standalone – ROOT_DIR=%s, DATA_DIR=%s, env=%s",
        root_dir,
        data_dir,
        env,
    )

    # En standalone on n'a pas les timings par étape → on passe des dicts vides
    compute_and_save_system_metrics(
        data_dir=data_dir,
        env=env,
        step_timings={},
        step_status={},
    )


if __name__ == "__main__":
    main()
