from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_config
from .project_map import get_project_map

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Modèle de tâche
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class AssistantTask:
    """
    Représente une tâche que l'assistant peut exécuter (engine, route API, page React…)
    """
    id: str
    category: str  # ex: "analysis_engine", "trading_task", "api_route", "react_page"
    name: str
    status: TaskStatus = TaskStatus.PENDING
    notes: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "name": self.name,
            "status": self.status.value,
            "notes": self.notes,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssistantTask":
        return cls(
            id=data["id"],
            category=data.get("category", "unknown"),
            name=data.get("name", data["id"]),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            notes=data.get("notes"),
            meta=data.get("meta") or {},
        )


# ---------------------------------------------------------------------------
# Gestion du fichier de persistance
# ---------------------------------------------------------------------------

def _get_tasks_path() -> Path:
    """
    Retourne le chemin du fichier assistant_tasks.json en fonction de la config.
    """
    cfg = get_config()
    data_dir = Path(cfg["data_dir"])
    state_dir = data_dir / "assistant"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "assistant_tasks.json"


def _seed_tasks_from_project_map() -> List[AssistantTask]:
    """
    Construit la liste des tâches initiales à partir du project_map.
    """
    pm = get_project_map()
    tasks: List[AssistantTask] = []

    # 1) Engines d'analyse
    for engine_name, engine_cfg in pm.get("analysis_engines", {}).items():
        tasks.append(
            AssistantTask(
                id=f"analysis_engine:{engine_name}",
                category="analysis_engine",
                name=engine_name,
                status=TaskStatus.PENDING,
                meta={
                    "module": engine_cfg.get("module"),
                    "entrypoint": engine_cfg.get("entrypoint"),
                    "output_file": engine_cfg.get("output_file"),
                },
            )
        )

    # 2) Tâches de trading (daily_trading_loop, etc.)
    for task_name, task_cfg in pm.get("trading_tasks", {}).items():
        tasks.append(
            AssistantTask(
                id=f"trading_task:{task_name}",
                category="trading_task",
                name=task_name,
                status=TaskStatus.PENDING,
                meta={
                    "module": task_cfg.get("module"),
                    "entrypoint": task_cfg.get("entrypoint"),
                    "description": task_cfg.get("description"),
                },
            )
        )

    # 3) Routes API
    api_routes = pm.get("api_routes", {})
    for top_key, value in api_routes.items():
        # Cas simple : racine et autres routes directes -> "root", "metrics", ...
        if isinstance(value, str):
            tasks.append(
                AssistantTask(
                    id=f"api_route:{top_key}",
                    category="api_route",
                    name=top_key,
                    status=TaskStatus.PENDING,
                    meta={"path": value},
                )
            )
        # Cas nested : "market": {"overview": "/market/overview", ...}
        elif isinstance(value, dict):
            for sub_key, sub_path in value.items():
                tasks.append(
                    AssistantTask(
                        id=f"api_route:{top_key}.{sub_key}",
                        category="api_route",
                        name=f"{top_key}.{sub_key}",
                        status=TaskStatus.PENDING,
                        meta={"path": sub_path},
                    )
                )

    # 4) Pages React
    react_pages = pm.get("react_pages", {})
    for group, paths in react_pages.items():
        for rel_path in paths:
            # ID déjà observée : "react_page:src_v2_interface_react_src_pages_Dashboard.jsx"
            safe_id = rel_path.replace("/", "_")
            tasks.append(
                AssistantTask(
                    id=f"react_page:{safe_id}",
                    category="react_page",
                    name=rel_path,
                    status=TaskStatus.PENDING,
                    meta={
                        "group": group,
                        "path": rel_path,
                    },
                )
            )

    logger.info("[assistant.tasks] Seeded %d tasks from project_map.", len(tasks))
    return tasks


def _load_tasks() -> List[AssistantTask]:
    """
    Charge les tâches depuis assistant_tasks.json, ou les seed si le fichier n'existe pas.
    """
    path = _get_tasks_path()
    if not path.exists():
        logger.info("[assistant.tasks] No assistant_tasks.json found, seeding from project_map.")
        tasks = _seed_tasks_from_project_map()
        _save_tasks(tasks)
        return tasks

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError:
        logger.warning("[assistant.tasks] assistant_tasks.json corrompu, régénération depuis project_map.")
        tasks = _seed_tasks_from_project_map()
        _save_tasks(tasks)
        return tasks

    if not isinstance(raw, list):
        logger.warning("[assistant.tasks] assistant_tasks.json invalide (pas une liste), régénération.")
        tasks = _seed_tasks_from_project_map()
        _save_tasks(tasks)
        return tasks

    tasks = [AssistantTask.from_dict(item) for item in raw]
    return tasks


def _save_tasks(tasks: List[AssistantTask]) -> None:
    """
    Sauvegarde la liste des tâches dans assistant_tasks.json.
    """
    path = _get_tasks_path()
    data = [t.to_dict() for t in tasks]
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("[assistant.tasks] Saved %d tasks to %s", len(tasks), path)


# ---------------------------------------------------------------------------
# API publique pour executor.py
# ---------------------------------------------------------------------------

def load_tasks() -> List[AssistantTask]:
    """
    Wrapper public utilisé par executor.py.
    """
    return _load_tasks()


def save_tasks(tasks: List[AssistantTask]) -> None:
    """
    Wrapper public utilisé par executor.py.
    """
    _save_tasks(tasks)


# ---------------------------------------------------------------------------
# Utilitaires divers
# ---------------------------------------------------------------------------

def _filter_tasks_by_status(tasks: List[AssistantTask], status: Optional[str]) -> List[AssistantTask]:
    if status is None:
        return tasks
    try:
        st = TaskStatus(status)
    except ValueError:
        # Status inconnu -> on renvoie la liste vide
        return []
    return [t for t in tasks if t.status == st]


def _reset_tasks() -> List[AssistantTask]:
    """
    Réinitialise complètement les tâches depuis le project_map.
    """
    tasks = _seed_tasks_from_project_map()
    _save_tasks(tasks)
    return tasks


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Gestion des tâches de l'assistant NSC (mapping engines/API/pages)."
    )

    # Mode moderne avec sous-commandes : `tasks list ...`
    subparsers = parser.add_subparsers(dest="command")

    p_list = subparsers.add_parser("list", help="Lister les tâches.")
    p_list.add_argument(
        "--status",
        choices=[s.value for s in TaskStatus],
        help="Filtrer par statut.",
    )

    subparsers.add_parser("reset", help="Réinitialiser les tâches depuis le project_map.")

    # Mode legacy : `--list --status pending` (déjà utilisé dans tes tests)
    parser.add_argument(
        "--list",
        action="store_true",
        help=argparse.SUPPRESS,  # on ne l'affiche pas dans le help, c'est pour compatibilité
    )
    parser.add_argument(
        "--status",
        dest="legacy_status",
        choices=[s.value for s in TaskStatus],
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args(argv)

    # ------------------------------------------------------------------
    # Mode legacy (sans sous-commande) : --list [--status ...]
    # ------------------------------------------------------------------
    if args.command is None:
        if args.list:
            tasks = load_tasks()
            filtered = _filter_tasks_by_status(tasks, args.legacy_status)
            print(json.dumps([t.to_dict() for t in filtered], indent=2, ensure_ascii=False))
            return
        else:
            # pas de sous-commande, pas de --list -> on affiche l'aide
            parser.print_help()
            return

    # ------------------------------------------------------------------
    # Mode moderne avec sous-commandes
    # ------------------------------------------------------------------
    if args.command == "list":
        tasks = load_tasks()
        filtered = _filter_tasks_by_status(tasks, args.status)
        print(json.dumps([t.to_dict() for t in filtered], indent=2, ensure_ascii=False))
        return

    if args.command == "reset":
        tasks = _reset_tasks()
        print(json.dumps([t.to_dict() for t in tasks], indent=2, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
