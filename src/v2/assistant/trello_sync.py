import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .config import get_config


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers chargement fichiers
# ---------------------------------------------------------------------------

def load_season2_upgrades() -> Dict[str, Any]:
    """
    Charge data/meta/season2_upgrades.json
    """
    cfg = get_config()
    root = Path(cfg["root_dir"])
    path = root / "data" / "meta" / "season2_upgrades.json"

    if not path.exists():
        raise FileNotFoundError(f"Fichier season2_upgrades.json introuvable: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    modules = data.get("modules", [])
    logger.info(
        "[trello_sync] season2_upgrades.json chargé (%s, modules=%d).",
        path,
        len(modules),
    )
    return data


def load_trello_export(path_str: str) -> Dict[str, Any]:
    """
    Charge un export Trello JSON (offline ou board_live.json).
    path_str est relatif au root_dir si non absolu.
    """
    cfg = get_config()
    root = Path(cfg["root_dir"])

    path = Path(path_str)
    if not path.is_absolute():
        path = root / path

    if not path.exists():
        raise FileNotFoundError(f"Fichier Trello introuvable: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cards = data.get("cards", [])
    lists = data.get("lists", [])
    logger.info(
        "[trello_sync] Export Trello chargé (%s, cards=%d, lists=%d).",
        path,
        len(cards),
        len(lists),
    )
    return data


# ---------------------------------------------------------------------------
# Helpers Trello API
# ---------------------------------------------------------------------------

def _trello_env():
    key = os.environ.get("TRELLO_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    board_id = os.environ.get("TRELLO_BOARD_ID")
    if not key or not token or not board_id:
        raise RuntimeError(
            "TRELLO_KEY, TRELLO_TOKEN ou TRELLO_BOARD_ID manquant dans l'environnement."
        )
    return key, token, board_id


def trello_get_board() -> Dict[str, Any]:
    """
    Récupère le board complet (cartes + listes) via l'API Trello.
    """
    key, token, board_id = _trello_env()
    url = f"https://api.trello.com/1/boards/{board_id}"
    params = {
        "key": key,
        "token": token,
        "cards": "all",
        "lists": "all",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Matching modules <-> cartes
# ---------------------------------------------------------------------------

def _list_id_to_name(trello: Dict[str, Any]) -> Dict[str, str]:
    return {lst["id"]: lst.get("name", "") for lst in trello.get("lists", [])}


def _find_cards_for_title(trello: Dict[str, Any], title: str) -> List[Dict[str, Any]]:
    """
    Retourne toutes les cartes dont le titre contient le module_title (case-insensitive).
    """
    res = []
    needle = title.lower()
    for c in trello.get("cards", []):
        name = c.get("name", "")
        if needle in name.lower():
            res.append(c)
    return res


def _get_list_name(trello: Dict[str, Any], list_id: str) -> str:
    mapping = _list_id_to_name(trello)
    return mapping.get(list_id, "<unknown>")


def _status_from_list_name(list_name: Optional[str]) -> str:
    if not list_name:
        return "missing"

    mapping = {
        "todo": ["Préprod – À faire", "À faire", "Todo"],
        "in_progress": ["Préprod – En cours", "En cours"],
        "done": ["Préprod – Terminé", "Terminé"],
    }
    for status, names in mapping.items():
        if list_name in names:
            return status
    return "unknown"


def _target_list_for_status(status: str, list_map: Dict[str, List[str]]) -> Optional[str]:
    """
    Retourne le nom de liste cible (exact) pour un statut logique (todo/in_progress/done).
    On prend le premier nom défini dans list_map[status].
    """
    names = list_map.get(status)
    if not names:
        return None
    return names[0]


# ---------------------------------------------------------------------------
# Sous-commandes
# ---------------------------------------------------------------------------

def cmd_list_modules(args) -> Dict[str, Any]:
    """
    Affiche simplement la liste des modules Season 2 et leur nombre.
    """
    season2 = load_season2_upgrades()
    modules = season2.get("modules", [])
    return {
        "modules": modules,
        "count": len(modules),
    }


def cmd_plan(args) -> Dict[str, Any]:
    """
    Compare season2_upgrades.json et un export Trello offline.
    Permet de voir quels modules ont déjà une carte, lesquels manquent, et les ambiguïtés.
    """
    cfg = get_config()
    root = Path(cfg["root_dir"])

    season2 = load_season2_upgrades()
    trello = load_trello_export(args.trello_json)

    modules = season2.get("modules", [])

    matched: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []
    ambiguous: List[Dict[str, Any]] = []

    for module in modules:
        mid = module.get("id")
        title = module.get("title", "")
        category = module.get("category")
        priority = module.get("priority")

        cards = _find_cards_for_title(trello, title)

        if not cards:
            missing.append(
                {
                    "module_id": mid,
                    "module_title": title,
                    "category": category,
                    "priority": priority,
                }
            )
        elif len(cards) == 1:
            card = cards[0]
            list_name = _get_list_name(trello, card.get("idList", ""))
            matched.append(
                {
                    "module_id": mid,
                    "module_title": title,
                    "card_id": card.get("id"),
                    "card_name": card.get("name"),
                    "list_id": card.get("idList"),
                    "list_name": list_name,
                    "category": category,
                    "priority": priority,
                }
            )
        else:
            # Plusieurs cartes candidates → ambigu
            candidates = []
            for c in cards:
                candidates.append(
                    {
                        "card_id": c.get("id"),
                        "card_name": c.get("name"),
                        "list_id": c.get("idList"),
                        "list_name": _get_list_name(trello, c.get("idList", "")),
                    }
                )
            ambiguous.append(
                {
                    "module_id": mid,
                    "module_title": title,
                    "category": category,
                    "priority": priority,
                    "candidates": candidates,
                }
            )

    return {
        "config": {
            "root_dir": str(root),
            "trello_json": args.trello_json,
        },
        "season2": {
            "modules_count": len(modules),
        },
        "plan": {
            "matched": matched,
            "missing": missing,
            "ambiguous": ambiguous,
        },
    }


def cmd_pull_board(args) -> Dict[str, Any]:
    """
    Récupère l'état live du board Trello via API,
    et l'enregistre dans data/trello/board_live.json
    """
    cfg = get_config()
    root = Path(cfg["root_dir"])
    out_path = root / "data" / "trello" / "board_live.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    board = trello_get_board()
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)

    cards = len(board.get("cards", []))
    lists = len(board.get("lists", []))
    logger.info(
        "[trello_sync] Board Trello exporté dans %s (cards=%d, lists=%d).",
        out_path,
        cards,
        lists,
    )
    return {
        "path": str(out_path),
        "cards": cards,
        "lists": lists,
    }


def cmd_sync_status(args) -> Dict[str, Any]:
    """
    Lit un export Trello (souvent board_live.json) et mappe
    chaque module Season2 sur un statut (todo / in_progress / done / missing / unknown).
    """
    cfg = get_config()
    root = Path(cfg["root_dir"])

    season2 = load_season2_upgrades()
    trello = load_trello_export(args.trello_json)

    modules = season2.get("modules", [])
    modules_info: List[Dict[str, Any]] = []

    for module in modules:
        mid = module.get("id")
        title = module.get("title", "")
        priority = module.get("priority")

        cards = _find_cards_for_title(trello, title)
        if not cards:
            modules_info.append(
                {
                    "id": mid,
                    "title": title,
                    "priority": priority,
                    "status": "missing",
                    "card_id": None,
                    "list_name": None,
                }
            )
            continue

        # On prend la première carte trouvée comme carte "référence"
        card = cards[0]
        list_name = _get_list_name(trello, card.get("idList", ""))
        status = _status_from_list_name(list_name)

        modules_info.append(
            {
                "id": mid,
                "title": title,
                "priority": priority,
                "status": status,
                "card_id": card.get("id"),
                "list_name": list_name,
            }
        )

    # Stats
    from collections import Counter

    counter = Counter(m["status"] for m in modules_info)
    stats = {
        "total_modules": len(modules_info),
        "by_status": dict(counter),
    }

    return {
        "config": {
            "root_dir": str(root),
            "trello_json": args.trello_json,
        },
        "stats": stats,
        "modules": modules_info,
    }


def cmd_sync_apply(args) -> Dict[str, Any]:
    """
    Applique la synchronisation Trello <-> Season2 modules.
    Peut fonctionner en dry-run (aucune modification réelle).
    """

    dry = getattr(args, "dry_run", True)  # par défaut dry-run

    season2 = load_season2_upgrades()
    trello = load_trello_export(args.trello_json)

    # Mapping des listes Trello
    list_map = {
        "todo": ["Préprod – À faire", "À faire", "Todo"],
        "in_progress": ["Préprod – En cours", "En cours"],
        "done": ["Préprod – Terminé", "Terminé"],
    }

    actions: List[Dict[str, Any]] = []

    modules = season2.get("modules", [])
    for module in modules:
        mid = module.get("id")
        title = module.get("title", "")
        category = module.get("category")
        priority = module.get("priority")

        # Utilisation du statut actuel pour décider de la liste cible (mode simple)
        # Option future : lire un statut "cible" dans season2_upgrades.json
        # Pour l'instant on dérive un statut logique à partir de la liste actuelle.
        cards = _find_cards_for_title(trello, title)

        if not cards:
            actions.append(
                {
                    "module_id": mid,
                    "module_title": title,
                    "category": category,
                    "priority": priority,
                    "action": "missing_card",
                    "notes": "Aucune carte trouvée pour ce module",
                }
            )
            continue

        card = cards[0]
        current_list = _get_list_name(trello, card.get("idList", ""))

        # Statut logique actuel basé sur la liste
        current_status = _status_from_list_name(current_list)

        # Politique simple :
        # - missing/unknown -> todo
        # - todo reste todo
        # - in_progress reste in_progress
        # - done reste done
        if current_status in ("missing", "unknown"):
            target_status = "todo"
        else:
            target_status = current_status

        target_list = _target_list_for_status(target_status, list_map)

        if not target_list:
            actions.append(
                {
                    "module_id": mid,
                    "module_title": title,
                    "category": category,
                    "priority": priority,
                    "card_id": card.get("id"),
                    "from": current_list,
                    "to": None,
                    "action": "error",
                    "notes": f"Aucune liste cible définie pour status={target_status}",
                }
            )
            continue

        if current_list == target_list:
            actions.append(
                {
                    "module_id": mid,
                    "module_title": title,
                    "category": category,
                    "priority": priority,
                    "card_id": card.get("id"),
                    "from": current_list,
                    "to": target_list,
                    "action": "noop",
                    "notes": "Déjà à la bonne place",
                }
            )
            continue

        # Déplacement nécessaire
        actions.append(
            {
                "module_id": mid,
                "module_title": title,
                "category": category,
                "priority": priority,
                "card_id": card.get("id"),
                "from": current_list,
                "to": target_list,
                "action": "move",
            }
        )

    # --- DRY RUN ---
    if dry:
        return {
            "dry_run": True,
            "actions": actions,
        }

    # --- APPLY ---
    key, token, board_id = _trello_env()
    list_ids = {lst["name"]: lst["id"] for lst in trello.get("lists", [])}

    applied: List[Dict[str, Any]] = []

    for a in actions:
        if a.get("action") != "move":
            continue

        target = a.get("to")
        if target not in list_ids:
            applied.append(
                {
                    "module_id": a.get("module_id"),
                    "card_id": a.get("card_id"),
                    "from": a.get("from"),
                    "to": target,
                    "status": "error",
                    "error": f"Liste inconnue: {target}",
                }
            )
            continue

        url = f"https://api.trello.com/1/cards/{a['card_id']}"
        params = {
            "key": key,
            "token": token,
            "idList": list_ids[target],
        }

        r = requests.put(url, params=params)
        if r.status_code == 200:
            applied.append(
                {
                    "module_id": a.get("module_id"),
                    "card_id": a.get("card_id"),
                    "from": a.get("from"),
                    "to": target,
                    "status": "applied",
                }
            )
        else:
            applied.append(
                {
                    "module_id": a.get("module_id"),
                    "card_id": a.get("card_id"),
                    "from": a.get("from"),
                    "to": target,
                    "status": "error",
                    "error": f"Trello API error {r.status_code}",
                }
            )

    return {
        "dry_run": False,
        "applied": applied,
        "total_applied": len(applied),
    }


# ---------------------------------------------------------------------------
# main / CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trello_sync.py",
        description="Synchronisation Trello <-> Season2 upgrades NSC",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-modules
    p_list = subparsers.add_parser(
        "list-modules",
        help="Liste les modules Season2 connus",
    )
    p_list.set_defaults(func=cmd_list_modules)

    # plan
    p_plan = subparsers.add_parser(
        "plan",
        help="Plan de mapping modules <-> cartes Trello (export offline)",
    )
    p_plan.add_argument(
        "--trello-json",
        required=True,
        help="Chemin vers l'export Trello JSON",
    )
    p_plan.set_defaults(func=cmd_plan)

    # pull-board
    p_pull = subparsers.add_parser(
        "pull-board",
        help="Récupère l'état live du board Trello via API",
    )
    p_pull.set_defaults(func=cmd_pull_board)

    # sync-status
    p_status = subparsers.add_parser(
        "sync-status",
        help="Affiche le statut de chaque module Season2 sur le board Trello",
    )
    p_status.add_argument(
        "--trello-json",
        required=True,
        help="Chemin vers l'export Trello JSON (souvent data/trello/board_live.json)",
    )
    p_status.set_defaults(func=cmd_sync_status)

    # sync-apply
    p_apply = subparsers.add_parser(
        "sync-apply",
        help="Applique la synchronisation Trello <-> Season2",
    )
    p_apply.add_argument(
        "--trello-json",
        required=True,
        help="Chemin vers l'export Trello JSON (souvent data/trello/board_live.json)",
    )
    p_apply.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne fait que simuler les changements (défaut).",
    )
    p_apply.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Applique réellement les changements.",
    )
    p_apply.set_defaults(func=cmd_sync_apply, dry_run=True)

    return parser


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args()

    try:
        out = args.func(args)
        if out is None:
            return
        print(json.dumps(out, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("[trello_sync] Erreur: %s", e, exc_info=True)
        print("null")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
