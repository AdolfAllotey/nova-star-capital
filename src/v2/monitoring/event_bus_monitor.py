import argparse
import json
import logging
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

from src.v2.utils.file_utils import get_data_dir

logger = logging.getLogger(__name__)


def _setup_logging(level: str = "INFO") -> None:
    """
    Configure le logging de base si rien n'est configuré.
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))


def load_last_events(
    events_path: Path,
    limit: int = 50,
    severity_filter=None,
    type_filter=None,
) -> list[dict]:
    """
    Charge les derniers events depuis event_bus.jsonl.

    - limit : nombre max d'events à renvoyer (FIFO, les plus anciens en premier).
    - severity_filter : ensemble/list de niveaux à conserver (ex: {"info","critical"}), ou None pour tout.
    - type_filter : ensemble/list de types d'event (ex: {"orchestrator.state"}), ou None pour tout.
    """
    if severity_filter is not None:
        severity_filter = {s.lower() for s in severity_filter}
    if type_filter is not None:
        type_filter = set(type_filter)

    if not events_path.exists():
        logger.warning("[event_bus_monitor] Fichier inexistant: %s", events_path)
        return []

    buffer: deque[dict] = deque(maxlen=limit)

    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("[event_bus_monitor] Ligne JSON invalide ignorée: %s", line[:120])
                continue

            sev = str(event.get("severity", "")).lower()
            typ = event.get("type")

            if severity_filter is not None and sev not in severity_filter:
                continue
            if type_filter is not None and typ not in type_filter:
                continue

            buffer.append(event)

    return list(buffer)


def summarize_events(events: list[dict]) -> dict:
    """
    Retourne un petit résumé statistique des events.
    """
    by_severity = Counter()
    by_type = Counter()
    sources = Counter()

    for evt in events:
        by_severity[str(evt.get("severity", "")).lower()] += 1
        by_type[evt.get("type", "unknown")] += 1
        sources[evt.get("source", "unknown")] += 1

    return {
        "total": len(events),
        "by_severity": dict(by_severity),
        "by_type": dict(by_type),
        "by_source": dict(sources),
    }


def format_event_line(evt: dict) -> str:
    """
    Formatte une ligne d'event de manière lisible pour le terminal.
    """
    ts = evt.get("timestamp") or evt.get("payload", {}).get("timestamp")
    sev = str(evt.get("severity", "")).upper() or "-"
    typ = evt.get("type", "-")
    src = evt.get("source", "-")

    # Petit résumé contextuel (pour orchestrator.state notamment)
    payload = evt.get("payload", {})
    mode = payload.get("mode")
    can_trade = payload.get("can_trade")
    gov_flag = payload.get("governance_flag")
    exec_flag = payload.get("execution_flag")
    bp_mode = payload.get("backpressure_mode")

    extras = []
    if mode is not None:
        extras.append(f"mode={mode}")
    if can_trade is not None:
        extras.append(f"can_trade={can_trade}")
    if gov_flag is not None:
        extras.append(f"gov={gov_flag}")
    if exec_flag is not None:
        extras.append(f"exec={exec_flag}")
    if bp_mode is not None:
        extras.append(f"bp={bp_mode}")

    extra_str = " | " + ", ".join(extras) if extras else ""

    return f"{ts or '-'} [{sev}] {typ} (src={src}){extra_str}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NSC Event Bus Monitor – lecture de data/telemetry/event_bus.jsonl"
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=50,
        help="Nombre maximum d'events à afficher (par défaut: 50)",
    )
    parser.add_argument(
        "--severity",
        type=str,
        default=None,
        help="Filtre sur la sévérité, liste séparée par des virgules (ex: info,warning,critical)",
    )
    parser.add_argument(
        "--type",
        dest="event_type",
        type=str,
        default=None,
        help="Filtre sur le type d'event (ex: orchestrator.state). "
             "Plusieurs types possibles séparés par des virgules.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="N'affiche que le résumé agrégé (pas la liste détaillée des events).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Affiche les events bruts au format JSON (une ligne par event).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Niveau de log (DEBUG, INFO, WARNING, ERROR). Par défaut: INFO",
    )

    args = parser.parse_args()

    _setup_logging(args.log_level)

    data_dir = Path(get_data_dir())
    events_path = data_dir / "telemetry" / "event_bus.jsonl"

    logger.info("[event_bus_monitor] DATA_DIR=%s", data_dir)
    logger.info("[event_bus_monitor] Lecture des events depuis %s", events_path)

    severity_filter = None
    if args.severity:
        severity_filter = [s.strip() for s in args.severity.split(",") if s.strip()]

    type_filter = None
    if args.event_type:
        type_filter = [t.strip() for t in args.event_type.split(",") if t.strip()]

    events = load_last_events(
        events_path=events_path,
        limit=args.limit,
        severity_filter=severity_filter,
        type_filter=type_filter,
    )

    summary = summarize_events(events)

    print("=== NSC Event Bus – Résumé ===")
    print(f"Total events retenus : {summary['total']}")
    print(f"Par sévérité       : {summary['by_severity']}")
    print(f"Par type           : {summary['by_type']}")
    print(f"Par source         : {summary['by_source']}")
    print("")

    if args.summary_only:
        return

    if not events:
        print("Aucun event trouvé avec les filtres donnés.")
        return

    print(f"=== Derniers events (max {args.limit}) ===")
    # On affiche du plus ancien au plus récent (ordre déjà respecté par load_last_events)
    for evt in events:
        if args.json:
            print(json.dumps(evt, ensure_ascii=False))
        else:
            print(format_event_line(evt))


if __name__ == "__main__":
    main()
