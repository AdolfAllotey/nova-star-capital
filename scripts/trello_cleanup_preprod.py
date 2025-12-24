#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Trello Preprod Cleanup (NSC)
- Dry-run by default
- Moves cards from a source list (e.g., "Préprod à faire") to target lists based on heuristics:
  * Keywords in title
  * Labels presence
  * Due date presence
  * Simple "done" detection

Auth:
- Uses env vars: TRELLO_API_KEY, TRELLO_TOKEN
Input:
- Either --board-id (preferred) OR --board-json export path (to extract board id)
Usage examples:
  python scripts/trello_cleanup_preprod.py --board-json ./nsc-crypto-production-2.json
  python scripts/trello_cleanup_preprod.py --board-id <BOARD_ID> --source "Préprod à faire"
  python scripts/trello_cleanup_preprod.py --board-id <BOARD_ID> --apply
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests


API_BASE = "https://api.trello.com/1"


def env(name: str, required: bool = True) -> str:
    v = os.getenv(name)
    if required and not v:
        print(f"[ERROR] Missing env var: {name}", file=sys.stderr)
        sys.exit(2)
    return v or ""


def trello_get(path: str, params: Dict[str, Any]) -> Any:
    url = f"{API_BASE}{path}"
    r = requests.get(url, params=params, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"GET {path} failed: {r.status_code} {r.text}")
    return r.json()


def trello_put(path: str, params: Dict[str, Any]) -> Any:
    url = f"{API_BASE}{path}"
    r = requests.put(url, params=params, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"PUT {path} failed: {r.status_code} {r.text}")
    return r.json()


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def load_board_id_from_export(board_json_path: str) -> str:
    with open(board_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bid = data.get("id")
    if not bid:
        raise RuntimeError("Could not find 'id' in board export json.")
    return bid


def fetch_lists(board_id: str, key: str, token: str) -> List[Dict[str, Any]]:
    # include closed=false to keep current lists only; you can change if needed
    return trello_get(f"/boards/{board_id}/lists", {"key": key, "token": token, "cards": "none"})


def fetch_cards_on_board(board_id: str, key: str, token: str) -> List[Dict[str, Any]]:
    # Pull enough fields to classify + move
    fields = "id,name,idList,closed,labels,due,dueComplete,url"
    return trello_get(f"/boards/{board_id}/cards", {"key": key, "token": token, "fields": fields})


def build_list_index(lists: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Returns:
      - id_by_name_norm: normalized list name -> list id
      - name_by_id: list id -> list name
    """
    id_by_name_norm: Dict[str, str] = {}
    name_by_id: Dict[str, str] = {}
    for lst in lists:
        lid = lst["id"]
        name = lst.get("name", "")
        name_by_id[lid] = name
        id_by_name_norm[normalize(name)] = lid
    return id_by_name_norm, name_by_id


def parse_due(due: Optional[str]) -> Optional[datetime]:
    if not due:
        return None
    # Trello returns ISO8601 with Z
    try:
        return datetime.fromisoformat(due.replace("Z", "+00:00"))
    except Exception:
        return None


def classify_card(
    card: Dict[str, Any],
    source_list_name: str,
    now_utc: datetime,
) -> Tuple[str, str]:
    """
    Returns: (bucket, reason)
    Buckets map to your target lists.
    """

    title = card.get("name", "")
    title_n = normalize(title)

    labels = card.get("labels") or []
    label_names = [normalize(l.get("name", "")) for l in labels if isinstance(l, dict)]
    label_join = " | ".join(label_names)

    due_dt = parse_due(card.get("due"))
    has_due = due_dt is not None
    overdue = bool(due_dt and due_dt < now_utc)

    # -------- Rules (edit freely) --------
    # 1) "done"/"merged"/"ok" keywords -> Préprod terminé
    if re.search(r"\b(done|termin[ée]|fait|ok|valid[ée]|merged|livr[ée])\b", title_n):
        return ("Préprod terminé", "keyword_done")

    # 2) Strong production/post-prod keywords -> Production suivi & amélioration continue
    if re.search(r"\b(post[- ]?prod|monitoring continu|amélioration continue|observability|hardening|defense[- ]in[- ]depth)\b", title_n):
        return ("Production suivi et améliorations continu", "keyword_postprod")

    # 3) Production preparation keywords -> Production à préparer / Production prêt
    if re.search(r"\b(release|deploy|déploiement|caddy|dns|ssl|prod|production)\b", title_n):
        # if due is soon/overdue -> "Production prêt" else "production à préparer"
        if overdue or (due_dt and (due_dt - now_utc).days <= 7):
            return ("Production – Prêt", "keyword_prod_due_soon")
        return ("production à préparer", "keyword_prod")

    # 4) Review/test keywords OR review label -> Préprod en revue / test
    if re.search(r"\b(test|tests|review|revue|qa|validation|smoke|e2e)\b", title_n):
        return ("Préprod en revue / test", "keyword_review")
    if any(x in label_join for x in ["review", "qa", "test"]):
        return ("Préprod en revue / test", "label_review")

    # 5) In-progress keywords OR in-progress label -> Préprod en cours
    if re.search(r"\b(wip|en cours|in progress|doing|implémentation|refacto|debug)\b", title_n):
        return ("Préprod en cours", "keyword_in_progress")
    if any(x in label_join for x in ["wip", "in progress", "doing", "en cours"]):
        return ("Préprod en cours", "label_in_progress")

    # 6) Default: keep in source (no move)
    return ("__KEEP__", "no_rule_match")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board-id", help="Trello board id (preferred).")
    ap.add_argument("--board-json", help="Path to Trello board export JSON to extract board id.")
    ap.add_argument("--source", default="Préprod à faire", help="Source list name to clean.")
    ap.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run).")
    ap.add_argument("--limit", type=int, default=0, help="Max number of moves (0 = no limit).")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    key = env("TRELLO_API_KEY")
    token = env("TRELLO_TOKEN")

    board_id = args.board_id
    if not board_id and args.board_json:
        board_id = load_board_id_from_export(args.board_json)

    if not board_id:
        print("[ERROR] Provide --board-id or --board-json", file=sys.stderr)
        return 2

    lists = fetch_lists(board_id, key, token)
    id_by_name_norm, name_by_id = build_list_index(lists)

    # Your target lists (names must match exactly what you have in Trello)
    targets = [
        "Préprod en cours",
        "Préprod en revue / test",
        "Préprod terminé",
        "Production – Prêt",
        "Production suivi et améliorations continu",
        "production à préparer",
    ]

    missing_targets = [t for t in targets if normalize(t) not in id_by_name_norm]
    if missing_targets:
        print("[WARN] These target lists were not found on board (names must match):")
        for t in missing_targets:
            print("  -", t)
        print("=> The script will still run, but moves to missing lists will be skipped.")

    source_id = id_by_name_norm.get(normalize(args.source))
    if not source_id:
        print(f"[ERROR] Source list not found: {args.source}", file=sys.stderr)
        print("Existing lists on board:")
        for lst in lists:
            print(" -", lst.get("name"))
        return 2

    cards = fetch_cards_on_board(board_id, key, token)

    now_utc = datetime.now(timezone.utc)
    plan: List[Dict[str, Any]] = []

    for card in cards:
        if card.get("closed"):
            continue
        if card.get("idList") != source_id:
            continue

        bucket, reason = classify_card(card, args.source, now_utc)
        if bucket == "__KEEP__":
            continue

        target_id = id_by_name_norm.get(normalize(bucket))
        if not target_id:
            # can't move if target list doesn't exist
            if args.verbose:
                print(f"[SKIP] target list missing for bucket={bucket} card={card.get('name')}")
            continue

        plan.append(
            {
                "card_id": card["id"],
                "card_name": card.get("name", ""),
                "from": args.source,
                "to": bucket,
                "reason": reason,
                "url": card.get("url", ""),
            }
        )

    # Apply limit
    if args.limit and len(plan) > args.limit:
        plan = plan[: args.limit]

    print(f"\n[PLAN] Source='{args.source}' => {len(plan)} card(s) to move")
    for i, item in enumerate(plan, 1):
        print(f"{i:03d} | {item['from']} -> {item['to']} | {item['reason']} | {item['card_name']}")

    if not args.apply:
        print("\n[DRY-RUN] No changes applied. Re-run with --apply to execute moves.")
        return 0

    # Execute moves
    moved = 0
    for item in plan:
        to_id = id_by_name_norm[normalize(item["to"])]
        trello_put(
            f"/cards/{item['card_id']}",
            {"key": key, "token": token, "idList": to_id},
        )
        moved += 1

    print(f"\n[OK] Applied: moved {moved} card(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
