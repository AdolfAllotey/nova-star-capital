# src/v2/monitoring/service_agent_pro.py

from __future__ import annotations

import argparse
import importlib
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

from src.v2.utils.file_utils import get_data_dir, save_json_file
from src.v2.utils.logger import get_logger
from src.v2.core.message_bus import publish_event

logger = get_logger(__name__)


@dataclass
class ServiceConfig:
    """Configuration d'un service logique NSC."""
    name: str
    target: str  # module_path:func_name
    kind: str    # "monitoring", "analysis", "trading", etc.
    description: str


# 🧩 Registre des services gérés par l'agent
SERVICES: Dict[str, ServiceConfig] = {
    "system_metrics": ServiceConfig(
        name="system_metrics",
        target="src.v2.monitoring.system_metrics_pro:main",
        kind="monitoring",
        description="Capture un snapshot complet des métriques système / trading.",
    ),
    "backpressure": ServiceConfig(
        name="backpressure",
        target="src.v2.monitoring.backpressure_engine_pro:main",
        kind="monitoring",
        description="Évalue la charge, les erreurs et déclenche les modes normal/degraded/emergency.",
    ),
    "risk_engine": ServiceConfig(
        name="risk_engine",
        target="src.v2.analysis.risk_engine_pro:main",
        kind="analysis",
        description="Évalue le risque global par actif (risk_score, veto, size_multiplier...).",
    ),
    "governance": ServiceConfig(
        name="governance",
        target="src.v2.analysis.governance_engine_pro:main",
        kind="governance",
        description="Génère le score de gouvernance et les hard/soft blocks.",
    ),
    "production_protocol": ServiceConfig(
        name="production_protocol",
        target="src.v2.monitoring.production_protocol:main",
        kind="monitoring",
        description="Vérifie la check-list institutionnelle de production.",
    ),
    "orchestrator": ServiceConfig(
        name="orchestrator",
        target="src.v2.monitoring.orchestrator_pro:main",
        kind="monitoring",
        description="Synthèse globale (mode normal/degraded/emergency, can_trade).",
    ),
    "daily_loop": ServiceConfig(
        name="daily_loop",
        target="src.v2.monitoring.daily_loop_engine_pro:main",
        kind="monitoring",
        description="Pilote la boucle quotidienne institutionnelle (pre-flight, core-session, post-close).",
    ),
    "auto_recovery": ServiceConfig(
        name="auto_recovery",
        target="src.v2.monitoring.auto_recovery_engine_pro:main",
        kind="monitoring",
        description="Analyse l’état des moteurs et propose des scénarios d’auto-récupération.",
    ),
}


def _load_callable(target: str) -> Callable[[], None]:
    """
    Charge dynamiquement la fonction main() d'un module cible.

    Ex: "src.v2.monitoring.system_metrics_pro:main"
    """
    try:
        module_path, func_name = target.split(":", 1)
    except ValueError:
        raise ValueError(f"Target invalide (attendu 'module:func'): {target!r}")

    module = importlib.import_module(module_path)
    func = getattr(module, func_name, None)
    if func is None:
        raise AttributeError(f"Fonction {func_name!r} introuvable dans {module_path!r}")
    return func


def run_service(config: ServiceConfig, env: str, data_dir: Path) -> Dict:
    """
    Exécute un service (une fois), mesure durée et statut,
    puis renvoie un dict de statut.
    """
    logger.info(
        "[service_agent_pro] Lancement service '%s' (%s) – target=%s",
        config.name,
        config.kind,
        config.target,
    )
    start_ts = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    status = "ok"
    error: Optional[str] = None

    try:
        func = _load_callable(config.target)
        func()
    except Exception as exc:  # noqa: BLE001
        status = "error"
        error = f"{exc.__class__.__name__}: {exc}"
        logger.exception(
            "[service_agent_pro] Erreur pendant l'exécution du service '%s'", config.name
        )

    duration_s = round(time.perf_counter() - t0, 3)

    service_state = {
        "service": config.name,
        "kind": config.kind,
        "target": config.target,
        "status": status,
        "error": error,
        "duration_s": duration_s,
        "env": env,
        "started_at": start_ts.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }

    # Event bus : service.state
    severity = "critical" if status == "error" else "info"
    try:
        publish_event(
            event_type="service.state",
            source=f"service_agent_pro:{config.name}",
            payload=service_state,
            severity=severity,
        )
        logger.info(
            "[service_agent_pro] Event service.state publié pour '%s' (status=%s)",
            config.name,
            status,
        )
    except Exception:  # noqa: BLE001
        # L'event bus ne doit jamais bloquer l'agent
        logger.exception(
            "[service_agent_pro] Impossible de publier l'event service.state pour '%s'",
            config.name,
        )

    return service_state


def save_services_snapshot(
    data_dir: Path,
    env: str,
    services_states: Dict[str, Dict],
) -> None:
    """
    Sauvegarde un snapshot global des services dans
    data/telemetry/services_status.json
    """
    telemetry_dir = data_dir / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": env,
        "services": services_states,
    }
    out_path = telemetry_dir / "services_status.json"
    save_json_file(out_path, snapshot)
    logger.info(
        "[service_agent_pro] Snapshot des services sauvegardé dans %s",
        out_path,
    )


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NSC Service Agent PRO – exécute un service NSC (multi-services architecture)."
    )
    parser.add_argument(
        "--service",
        "-s",
        dest="service",
        default="all",
        help=(
            "Nom du service à lancer parmi : "
            + ", ".join(sorted(SERVICES.keys()))
            + " (default: all)"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)

    # DATA_DIR et ENV :
    data_dir = get_data_dir()
    env = "PREPROD"  # explicite pour l’instant

    if args.service != "all" and args.service not in SERVICES:
        logger.error(
            "[service_agent_pro] Service inconnu: %s. Services disponibles: %s",
            args.service,
            ", ".join(sorted(SERVICES.keys())),
        )
        sys.exit(1)

    services_to_run = (
        [SERVICES[args.service]]
        if args.service != "all"
        else [SERVICES[name] for name in sorted(SERVICES.keys())]
    )

    logger.info(
        "[service_agent_pro] Démarrage – env=%s, data_dir=%s, nb_services=%d",
        env,
        data_dir,
        len(services_to_run),
    )

    states: Dict[str, Dict] = {}
    for config in services_to_run:
        state = run_service(config, env=env, data_dir=data_dir)
        states[config.name] = state

    # Snapshot global
    save_services_snapshot(data_dir=data_dir, env=env, services_states=states)

    logger.info("[service_agent_pro] Terminé.")


if __name__ == "__main__":
    main()
