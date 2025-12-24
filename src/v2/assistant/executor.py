"""
Executor V3 pour l'assistant Nova Star Capital.

- s'appuie sur src.v2.assistant.tasks pour charger / sauvegarder les tâches
- utilise src.v2.assistant.project_map pour connaître les modules à appeler
- expose une CLI simple :
    python -m src.v2.assistant.executor status
    python -m src.v2.assistant.executor run-next --status pending
    python -m src.v2.assistant.executor run-all --status pending
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from .tasks import AssistantTask, load_tasks, save_tasks
from .project_map import get_project_map

logger = logging.getLogger(__name__)

if not logger.handlers:
    # Config simple, on laisse le root logger gérer les handlers globaux
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _run_analysis_engine(name: str) -> Dict[str, Any]:
    """Exécute un engine d'analyse déclaré dans project_map['analysis_engines']."""
    project_map = get_project_map()
    spec = project_map.get("analysis_engines", {}).get(name)

    if not spec:
        msg = f"Engine d'analyse inconnu dans project_map: {name}"
        logger.warning("[executor] %s", msg)
        return {"status": "skipped", "notes": msg}

    module_name = spec.get("module")
    entrypoint = spec.get("entrypoint", "main")

    start = time.time()
    try:
        logger.info(
            "[executor] Exécution de l'engine d'analyse '%s' (%s.%s)",
            name,
            module_name,
            entrypoint,
        )
        mod = importlib.import_module(module_name)
        func = getattr(mod, entrypoint)
        func()  # on laisse l'engine écrire ses propres fichiers JSON
        duration = time.time() - start
        logger.info("[executor] Engine '%s' exécuté en %.2fs.", name, duration)
        return {"status": "done", "notes": f"OK ({duration:.2f}s)"}
    except Exception as e:  # noqa: BLE001
        duration = time.time() - start
        logger.error(
            "[executor] Erreur lors de l'exécution de l'engine '%s': %s",
            name,
            e,
            exc_info=True,
        )
        return {
            "status": "error",
            "notes": f"Error after {duration:.2f}s: {e.__class__.__name__}: {e}",
        }


def _run_trading_task(name: str) -> Dict[str, Any]:
    """Exécute une trading task déclarée dans project_map['trading_tasks']."""
    project_map = get_project_map()
    spec = project_map.get("trading_tasks", {}).get(name)

    if not spec:
        msg = f"Trading task inconnue dans project_map: {name}"
        logger.warning("[executor] %s", msg)
        return {"status": "skipped", "notes": msg}

    module_name = spec.get("module")
    entrypoint = spec.get("entrypoint", "main")

    start = time.time()
    try:
        logger.info(
            "[executor] Exécution de la trading task '%s' (%s.%s)",
            name,
            module_name,
            entrypoint,
        )
        mod = importlib.import_module(module_name)
        func = getattr(mod, entrypoint)
        func()  # idem, la task écrit elle-même ses artefacts
        duration = time.time() - start
        logger.info(
            "[executor] Trading task '%s' exécutée en %.2fs.", name, duration
        )
        return {"status": "done", "notes": f"OK ({duration:.2f}s)"}
    except Exception as e:  # noqa: BLE001
        duration = time.time() - start
        logger.error(
            "[executor] Erreur lors de l'exécution de la trading task '%s': %s",
            name,
            e,
            exc_info=True,
        )
        return {
            "status": "error",
            "notes": f"Error after {duration:.2f}s: {e.__class__.__name__}: {e}",
        }


def _run_api_route(name: str) -> Dict[str, Any]:
    """
    Placeholder pour les tâches de type 'api_route'.

    Pour l’instant on marque en 'skipped' proprement.
    """
    msg = (
        "Génération automatique des routes API non encore implémentée "
        f"pour api_route:{name} (placeholder V3)."
    )
    logger.info("[executor] %s", msg)
    return {"status": "skipped", "notes": msg}


def _run_react_page(name: str) -> Dict[str, Any]:
    """
    Placeholder pour les tâches de type 'react_page'.

    À terme : génération / vérification de squelette React, etc.
    """
    msg = (
        "Gestion automatique des pages React non encore implémentée "
        f"pour react_page:{name} (placeholder V3)."
    )
    logger.info("[executor] %s", msg)
    return {"status": "skipped", "notes": msg}


def _run_single_task(task: AssistantTask) -> Dict[str, Any]:
    """
    Exécute une tâche unique (AssistantTask) et met à jour son statut.
    Retourne un dict prêt à être sérialisé en JSON.
    """
    task_id = task.id
    category = task.category

    logger.info(
        "[executor] Démarrage tâche %s (%s)", task_id, category
    )

    # On extrait la "clé logique" après le prefix "category:"
    name = task_id.split(":", 1)[1] if ":" in task_id else task_id

    if category == "analysis_engine":
        res = _run_analysis_engine(name)
    elif category == "trading_task":
        res = _run_trading_task(name)
    elif category == "api_route":
        res = _run_api_route(name)
    elif category == "react_page":
        res = _run_react_page(name)
    else:
        msg = f"Catégorie inconnue pour la tâche {task_id}: {category}"
        logger.warning("[executor] %s", msg)
        res = {"status": "skipped", "notes": msg}

    task.status = res.get("status", "done")
    task.notes = res.get("notes")

    return {
        "id": task.id,
        "status": task.status,
        "category": task.category,
        "notes": task.notes,
    }


# ---------------------------------------------------------------------------
# Fonctions publiques utilisées par la CLI
# ---------------------------------------------------------------------------

def get_status(status_filter: str = "all") -> List[Dict[str, Any]]:
    """
    Retourne la liste des tâches (dict) avec éventuellement un filtre de statut.

    status_filter ∈ {"all", "pending", "done", "error", "skipped"}
    """
    tasks = load_tasks()
    items = [t.to_dict() for t in tasks]

    if status_filter != "all":
        items = [t for t in items if t.get("status", "pending") == status_filter]

    return items


def run_next(status_filter: str = "pending") -> Dict[str, Any]:
    """
    Exécute la prochaine tâche ayant le statut `status_filter` (défaut: pending).
    Retourne un dict décrivant le résultat.
    """
    tasks = load_tasks()

    for task in tasks:
        if task.status == status_filter:
            result = _run_single_task(task)
            save_tasks(tasks)
            return result

    msg = f"Aucune tâche avec status='{status_filter}'"
    logger.info("[executor] %s", msg)
    return {
        "id": None,
        "status": "noop",
        "category": None,
        "notes": msg,
    }


def run_all(status_filter: str = "pending") -> List[Dict[str, Any]]:
    """
    Enchaîne toutes les tâches ayant le statut `status_filter`.
    Retourne la liste des résultats (dict).
    """
    tasks = load_tasks()
    results: List[Dict[str, Any]] = []

    for task in tasks:
        if task.status == status_filter:
            result = _run_single_task(task)
            results.append(result)

    save_tasks(tasks)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executor V3 pour les tâches Nova Star Capital."
    )
    subparsers = parser.add_subparsers(dest="command")

    # status
    p_status = subparsers.add_parser(
        "status", help="Afficher le statut des tâches."
    )
    p_status.add_argument(
        "--status",
        choices=["all", "pending", "done", "error", "skipped"],
        default="all",
        help="Filtrer les tâches par statut (défaut: all).",
    )

    # run-next
    p_next = subparsers.add_parser(
        "run-next", help="Exécuter la prochaine tâche avec un statut donné."
    )
    p_next.add_argument(
        "--status",
        default="pending",
        choices=["pending", "done", "error", "skipped"],
        help="Statut des tâches à cibler (défaut: pending).",
    )

    # run-all
    p_all = subparsers.add_parser(
        "run-all",
        help="Enchaîner toutes les tâches avec un statut donné.",
    )
    p_all.add_argument(
        "--status",
        default="pending",
        choices=["pending", "done", "error", "skipped"],
        help="Statut des tâches à cibler (défaut: pending).",
    )

    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    # Mode legacy : sans sous-commande → status all
    if args.command is None:
        items = get_status(status_filter="all")
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    if args.command == "status":
        items = get_status(status_filter=args.status)
        print(json.dumps(items, ensure_ascii=False, indent=2))
    elif args.command == "run-next":
        res = run_next(status_filter=args.status)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "run-all":
        items = run_all(status_filter=args.status)
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        parser.error(f"Commande inconnue: {args.command}")


if __name__ == "__main__":
    main()
