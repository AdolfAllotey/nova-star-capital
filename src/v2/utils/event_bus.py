# src/v2/utils/event_bus.py

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.v2.utils.file_utils import get_data_dir

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # fallback legacy
    from src.v2.logger import get_logger  # type: ignore


logger = get_logger("event_bus")


def _now_utc_str() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _events_path() -> Path:
    data_dir = Path(get_data_dir())
    return data_dir / "telemetry" / "event_bus.jsonl"


def publish_event(
    event_type: str,
    source: str,
    severity: str,
    payload: Dict[str, Any],
    events_path: Optional[Path] = None,
) -> bool:
    """
    Publication d'un event dans le bus JSONL.
    Utilise src.v2.core.message_bus.MessageBus + Event (format attendu par core).
    Retourne True si publié, False sinon.
    """

    try:
        from src.v2.core.message_bus import MessageBus, Event
    except Exception as exc:
        logger.warning("[event_bus] MessageBus/Event indisponibles (%s) – event non publié.", exc)
        return False

    path = events_path or _events_path()

    try:
        bus = MessageBus(events_path=path)  # Path (pas str)
        evt = Event(
            type=event_type,
            source=source,
            severity=severity,
            payload=payload,
            timestamp=_now_utc_str(),  # <-- FIX: string JSON-serializable
        )
        bus.publish(evt)  # publish(Event)
        logger.info("[event_bus] Event publié – type=%s, source=%s, severity=%s", event_type, source, severity)
        return True
    except Exception as exc:
        logger.error("[event_bus] Impossible de publier l'event %s : %s", event_type, exc, exc_info=True)
        return False
