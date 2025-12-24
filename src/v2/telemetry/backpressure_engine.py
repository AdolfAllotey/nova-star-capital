import os
from pathlib import Path
from typing import Any, Dict

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)

# Détection ROOT/DATA comme dans les autres modules
ROOT_DIR = Path(os.getenv("NSC_ROOT_DIR") or Path(__file__).resolve().parents[4]).resolve()
DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or (ROOT_DIR / "data")).resolve()

SYSTEM_METRICS_PATH = DATA_DIR / "telemetry" / "system_metrics.json"
ORCHESTRATOR_STATE_PATH = DATA_DIR / "telemetry" / "orchestrator_state.json"


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_mode(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Décide du mode système (normal / degraded / safe / emergency)
    à partir des system_metrics.json.

    Règles simples pour démarrer (évolutif) :
    - emergency :
        • nb_steps_error > 0
        • kill_switch_status in {"hard", "global_off"}
        • risk_on_off == "off"
        • governance_flag in {"hard_block", "emergency_stop"}
    - safe :
        • size_factor < 0.5
        • kill_switch_status == "soft" ou reason 'caution'
        • governance_flag == "soft_block"
    - degraded :
        • total_duration_sec > 5s ou nb_execution_attempts > 200
    - sinon : normal
    """

    reasons = []
    mode = "normal"
    backpressure_flag = "ok"

    total_duration = _to_float(metrics.get("total_duration_sec"), 0.0)
    nb_steps_error = _to_int(metrics.get("nb_steps_error"), 0)
    nb_exec_attempts = _to_int(metrics.get("nb_execution_attempts"), 0)

    kill_status = metrics.get("kill_switch_status")
    kill_reason = metrics.get("kill_switch_reason")
    gov_flag = metrics.get("governance_flag")
    gov_score = metrics.get("governance_score")

    risk_on_off = (metrics.get("risk_on_off") or "on").lower()
    size_factor = _to_float(metrics.get("risk_size_factor"), 0.0)

    # --- Emergency ---------------------------------------------------------
    if nb_steps_error > 0:
        mode = "emergency"
        backpressure_flag = "block"
        reasons.append(f"{nb_steps_error} step(s) en erreur")

    if kill_status in {"hard", "global_off"}:
        mode = "emergency"
        backpressure_flag = "block"
        reasons.append(f"kill_switch_status={kill_status}")

    if risk_on_off == "off":
        mode = "emergency"
        backpressure_flag = "block"
        reasons.append("risk_on_off=off")

    if gov_flag in {"hard_block", "emergency_stop"}:
        mode = "emergency"
        backpressure_flag = "block"
        reasons.append(f"governance_flag={gov_flag}")

    # --- Safe / Degraded (si pas déjà emergency) --------------------------
    if mode != "emergency":
        # Charge / lenteur
        if total_duration > 5.0 or nb_exec_attempts > 200:
            mode = "degraded"
            backpressure_flag = "caution"
            reasons.append(
                f"heavy_load: duration={total_duration:.2f}s, attempts={nb_exec_attempts}"
            )

        # Mode "safe" (réduction de la voilure)
        if size_factor and size_factor < 0.5:
            mode = "safe"
            backpressure_flag = "caution"
            reasons.append(f"reduced_size_factor={size_factor}")

        if kill_status == "soft" or (kill_reason and "caution" in str(kill_reason).lower()):
            mode = "safe"
            backpressure_flag = "caution"
            reasons.append("kill_switch soft/caution")

        if gov_flag == "soft_block":
            mode = "safe"
            backpressure_flag = "caution"
            reasons.append("governance_flag=soft_block")

    if not reasons:
        reasons.append("system nominal")

    return {
        "mode": mode,
        "backpressure_flag": backpressure_flag,
        "reasons": reasons,
        "metrics_snapshot": metrics,
        "governance_flag": gov_flag,
        "governance_score": gov_score,
    }


def main() -> None:
    logger.info("[backpressure_engine] DATA_DIR=%s", DATA_DIR)

    metrics = load_json_file(str(SYSTEM_METRICS_PATH), default=None)
    if not metrics:
        logger.warning(
            "[backpressure_engine] Aucun system_metrics.json trouvé (%s), backpressure ignoré.",
            SYSTEM_METRICS_PATH,
        )
        state = {
            "mode": "unknown",
            "backpressure_flag": "unknown",
            "reasons": ["no_system_metrics"],
            "metrics_snapshot": {},
            "governance_flag": None,
            "governance_score": None,
        }
    else:
        state = evaluate_mode(metrics)
        logger.info(
            "[backpressure_engine] Mode=%s, flag=%s, reasons=%s",
            state["mode"],
            state["backpressure_flag"],
            "; ".join(state["reasons"]),
        )

    save_json_file(str(ORCHESTRATOR_STATE_PATH), state)
    logger.info(
        "[backpressure_engine] orchestrator_state.json sauvegardé (%s).",
        ORCHESTRATOR_STATE_PATH,
    )


if __name__ == "__main__":
    main()
