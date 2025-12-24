# src/v2/operations/real_production_protocol.py

import os
import datetime as dt
from typing import Any, Dict, List

# ============================================================
# Logger - tentative d'utilisation du logger centralisé NSC,
# sinon fallback sur le logger standard Python.
# ============================================================
try:
    from src.v2.utils.logging_utils import get_logger  # si ton module existe à cet endroit
except ModuleNotFoundError:
    import logging

    def get_logger(name: str):
        """
        Fallback minimal si le module logging_utils n'est pas disponible.
        Utilise le logging standard Python.
        """
        logger = logging.getLogger(name)
        if not logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            )
        return logger

from src.v2.utils.file_utils import load_json_file, save_json_file

# ============================================================
# MessageBus – on essaie d'abord l'import relatif, puis l'absolu.
# Si rien ne marche, on désactive la publication d'events mais
# on garde la génération du JSON.
# ============================================================
MessageBus = None  # type: ignore[name-defined]

try:
    from ..monitoring.message_bus import MessageBus as _MB  # type: ignore[import]
    MessageBus = _MB
except Exception:
    try:
        from src.v2.monitoring.message_bus import MessageBus as _MB2  # type: ignore[import]
        MessageBus = _MB2
    except Exception:
        MessageBus = None  # type: ignore[assignment]

logger = get_logger(__name__)

DATA_DIR = os.getenv("NSC_DATA_DIR", "data")
OPERATIONS_DIR = os.path.join(DATA_DIR, "operations")
TELEMETRY_DIR = os.path.join(DATA_DIR, "telemetry")

CONFIG_PATH = os.path.join(OPERATIONS_DIR, "real_production_protocol_config.json")
STATE_PATH = os.path.join(OPERATIONS_DIR, "real_production_protocol_state.json")


def now_utc_iso() -> str:
    """
    Retourne un timestamp ISO8601 en UTC (aware), ex: 2025-12-11T19:45:00Z
    """
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_protocol_config() -> Dict[str, Any]:
    """
    Charge la configuration du Real Production Protocol.
    Si le fichier n'existe pas, on retourne un squelette par défaut.
    """
    default_config: Dict[str, Any] = {
        "current_phase": "preflight_48h",
        "phases": {
            "preflight_48h": {
                "checks": {
                    "infra_ready": False,
                    "secrets_ok": False,
                    "monitoring_ok": False,
                    "risk_engine_ok": False,
                    "backtests_recent_ok": False,
                }
            },
            "shadow_mode": {
                "checks": {
                    "shadow_enabled": False,
                    "shadow_vs_preprod_diff_ok": False,
                    "alerts_ok": False,
                }
            },
            "canary": {
                "checks": {
                    "canary_size_defined": False,
                    "canary_risk_limits_ok": False,
                    "kill_switch_ready": False,
                    "canary_results_ok": False,
                }
            },
            "full_production": {
                "checks": {
                    "governance_ok": False,
                    "daily_loop_defined": False,
                    "stress_tests_complete": False,
                }
            },
        },
    }

    config = load_json_file(CONFIG_PATH, default=default_config)
    if not isinstance(config, dict):
        logger.warning(
            "[real_production_protocol] Format inattendu pour %s (type=%s), "
            "utilisation de la configuration par défaut",
            CONFIG_PATH,
            type(config).__name__,
        )
        return default_config

    return config


def evaluate_phase_status(phase_name: str, phase_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Évalue le statut d'une phase donnée en fonction de ses checks.
    Renvoie :
      - status: blocked | in_progress | ready_to_advance
      - nb_checks_total, nb_checks_ok, nb_checks_ko
      - liste des checks détaillés
    """
    checks_cfg = phase_cfg.get("checks", {})
    if not isinstance(checks_cfg, dict):
        checks_cfg = {}

    checks: List[Dict[str, Any]] = []
    nb_total = 0
    nb_ok = 0
    nb_ko = 0

    for name, value in checks_cfg.items():
        nb_total += 1
        is_ok = bool(value)
        if is_ok:
            nb_ok += 1
        else:
            nb_ko += 1
        checks.append({"name": name, "ok": is_ok})

    if nb_total == 0:
        status = "in_progress"
    elif nb_ok == nb_total:
        status = "ready_to_advance"
    elif nb_ok == 0:
        status = "blocked"
    else:
        status = "in_progress"

    return {
        "phase": phase_name,
        "status": status,
        "nb_checks_total": nb_total,
        "nb_checks_ok": nb_ok,
        "nb_checks_ko": nb_ko,
        "checks": checks,
    }


def map_status_to_severity(status: str) -> str:
    """
    Map du statut de phase vers une sévérité event_bus.
    """
    if status == "ready_to_advance":
        return "info"
    if status == "in_progress":
        return "warning"
    return "error"  # blocked


def build_reasons(
    phase_name: str,
    phase_status: Dict[str, Any],
    env: str,
) -> List[str]:
    """
    Raison lisible pour l'UI / logs.
    """
    nb_total = phase_status.get("nb_checks_total", 0)
    nb_ok = phase_status.get("nb_checks_ok", 0)
    nb_ko = phase_status.get("nb_checks_ko", 0)
    status = phase_status.get("status", "in_progress")

    reasons = [
        f"Phase actuelle du Real Production Protocol = {phase_name} (env={env}).",
        f"Checks : {nb_ok}/{nb_total} OK, {nb_ko} restant(s).",
        f"Statut de la phase = {status}.",
    ]

    if nb_ko > 0:
        missing = [
            c["name"] for c in phase_status.get("checks", []) if not c.get("ok", False)
        ]
        reasons.append(
            "Checks manquants : " + ", ".join(missing)
            if missing
            else "Certains checks restent à valider."
        )

    return reasons


def run_real_production_protocol(env: str = "PREPROD") -> Dict[str, Any]:
    """
    1. Charge la config
    2. Évalue la phase courante
    3. Écrit un état lisible dans real_production_protocol_state.json
    4. Publie un event production.protocol.state (si MessageBus dispo)
    """
    logger.info("[real_production_protocol] DATA_DIR=%s, env=%s", DATA_DIR, env)

    config = load_protocol_config()
    current_phase = config.get("current_phase", "preflight_48h")
    phases_cfg = config.get("phases", {})
    phase_cfg = phases_cfg.get(current_phase, {"checks": {}})

    phase_status = evaluate_phase_status(current_phase, phase_cfg)

    state = {
        "timestamp": now_utc_iso(),
        "env": env,
        "current_phase": current_phase,
        "phase_status": phase_status,
        "reasons": build_reasons(current_phase, phase_status, env),
    }

    os.makedirs(OPERATIONS_DIR, exist_ok=True)
    save_json_file(STATE_PATH, state)
    logger.info(
        "[real_production_protocol] real_production_protocol_state.json sauvegardé "
        "(phase=%s, status=%s, nb_checks_ok=%s/%s)",
        current_phase,
        phase_status.get("status"),
        phase_status.get("nb_checks_ok"),
        phase_status.get("nb_checks_total"),
    )

    # Publication Message Bus
    if MessageBus is None:
        logger.warning(
            "[real_production_protocol] MessageBus introuvable – aucun event "
            "production.protocol.state ne sera publié."
        )
    else:
        os.makedirs(TELEMETRY_DIR, exist_ok=True)
        bus_path = os.path.join(TELEMETRY_DIR, "event_bus.jsonl")
        bus = MessageBus(events_path=bus_path)

        severity = map_status_to_severity(phase_status.get("status", "in_progress"))
        payload = {
            "env": env,
            "current_phase": current_phase,
            "phase_status": phase_status,
        }
        bus.publish(
            event_type="production.protocol.state",
            source="real_production_protocol",
            severity=severity,
            payload=payload,
        )
        logger.info(
            "[real_production_protocol] Event production.protocol.state publié "
            "(severity=%s, phase=%s, status=%s)",
            severity,
            current_phase,
            phase_status.get("status"),
        )

    return state


if __name__ == "__main__":
    env = os.getenv("NSC_ENV", "PREPROD")
    run_real_production_protocol(env=env)
