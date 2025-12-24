from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from src.v2.utils.logger import get_logger  # logger centralisé


# =============================================================================
# 1) Utilitaires internes
# =============================================================================

def get_data_dir(*args, **kwargs) -> Path:
    """
    Résout le répertoire DATA_DIR.

    Priorité :
    1. NSC_DATA_DIR (variable d'environnement)
    2. ./data (par défaut)

    *args / **kwargs sont ignorés mais acceptés pour rester compatible
    avec les anciens appels (fallback=..., env_var=..., etc.).
    """
    env_dir = os.getenv("NSC_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path("data")


def ensure_dir(path: Path) -> None:
    """Crée un dossier s'il n'existe pas."""
    path.mkdir(parents=True, exist_ok=True)


def append_jsonl(file_path: Path, obj: dict) -> None:
    """Ajoute une ligne JSON dans un fichier JSONL."""
    ensure_dir(file_path.parent)
    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


logger = get_logger("message_bus")


# =============================================================================
# 2) Modèle d’event du Message Bus
# =============================================================================

@dataclass
class Event:
    timestamp: str
    type: str
    source: str
    severity: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# 3) Bus interne (singleton)
# =============================================================================

class MessageBus:
    """
    Bus d’événements NSC (thread-safe, robuste, JSONL).
    """
    _instance: Optional["MessageBus"] = None
    _instance_lock: Lock = Lock()

    def __init__(self, events_path: Path):
        self.events_path = events_path
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        logger.info(f"[message_bus] Initialisation du Message Bus – events_path={events_path}")

    @classmethod
    def get_instance(cls, events_path: Path) -> "MessageBus":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = MessageBus(events_path)
            return cls._instance

    # ----------------------------------------------------------------------
    #  Publication d’un event
    # ----------------------------------------------------------------------
    def publish(self, evt: Event) -> None:
        payload = evt.to_dict()

        with self.lock:
            append_jsonl(self.events_path, payload)

        logger.info(
            f"[message_bus] Event publié – "
            f"type={evt.type}, source={evt.source}, severity={evt.severity}"
        )


# =============================================================================
# 4) Fonctions publiques utilisées par tous les modules NSC (PRO)
# =============================================================================

def get_message_bus() -> MessageBus:
    """
    Retourne l’instance du Message Bus NSC.
    Utilise DATA_DIR/telemetry/event_bus.jsonl
    """
    data_dir = get_data_dir()
    telemetry_dir = data_dir / "telemetry"
    events_path = telemetry_dir / "event_bus.jsonl"
    return MessageBus.get_instance(events_path)


def publish_event(*args: Any, **kwargs: Any) -> None:
    """
    API de publication d’events utilisée par tous les moteurs.

    ✅ Compatible avec les anciens appels positionnels :
        publish_event("metrics.snap", "system_metrics_pro", "critical", payload=...)

    ✅ Compatible avec les nouveaux appels nommés :
        publish_event(
            type="metrics.snap",
            source="system_metrics_pro",
            severity="critical",
            payload={...},
        )

    ✅ Si un paramètre est passé à la fois en positionnel et en nommé
       (ex : severity), la version **nommée** est prioritaire.
    """

    # ---- 1) Récupérer les éventuels arguments nommés ---------------------
    event_type = kwargs.pop("event_type", None) or kwargs.pop("type", None)
    source = kwargs.pop("source", None)
    severity = kwargs.pop("severity", None)
    payload = kwargs.pop("payload", None)

    # ---- 2) Compléter avec les positionnels si besoin --------------------
    # args = [event_type, source, severity] potentiels
    if len(args) > 0 and event_type is None:
        event_type = args[0]
    if len(args) > 1 and source is None:
        source = args[1]
    if len(args) > 2 and severity is None:
        severity = args[2]

    # ---- 3) Valeurs par défaut -------------------------------------------
    if event_type is None:
        raise ValueError("publish_event() requires an event_type (or type=...).")

    if severity is None:
        severity = "info"

    if payload is None:
        payload = {}

    # ---- 4) Construire et publier l’event --------------------------------
    evt = Event(
        timestamp=datetime.utcnow().isoformat() + "Z",
        type=event_type,
        source=source or "unknown",
        severity=severity,
        payload=payload,
    )

    bus = get_message_bus()
    bus.publish(evt)
