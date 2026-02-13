#!/usr/bin/env python3
import os, json, argparse, requests
from typing import Any, Dict, List, Optional

TRELLO_API_BASE = "https://api.trello.com/1"

def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def trello_post(path: str, params: Dict[str, Any]) -> Any:
    r = requests.post(f"{TRELLO_API_BASE}{path}", params=params, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Trello POST {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()

def trello_get(path: str, params: Dict[str, Any]) -> Any:
    r = requests.get(f"{TRELLO_API_BASE}{path}", params=params, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Trello GET {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()

def find_card(list_id: str, name: str, key: str, token: str) -> Optional[Dict[str, Any]]:
    cards = trello_get(f"/lists/{list_id}/cards", {
        "key": key, "token": token, "fields": "id,name"
    })
    for c in cards:
        if c.get("name") == name:
            return c
    return None

def create_card(list_id: str, name: str, desc: str, key: str, token: str) -> str:
    existing = find_card(list_id, name, key, token)
    if existing:
        return existing["id"]
    card = trello_post("/cards", {
        "key": key,
        "token": token,
        "idList": list_id,
        "name": name,
        "desc": desc,
        "pos": "bottom"
    })
    return card["id"]

def add_checklist(card_id: str, name: str, items: List[str], key: str, token: str):
    cl = trello_post(f"/cards/{card_id}/checklists", {
        "key": key,
        "token": token,
        "name": name
    })
    for it in items:
        trello_post(f"/checklists/{cl['id']}/checkItems", {
            "key": key,
            "token": token,
            "name": it,
            "pos": "bottom"
        })

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    args = ap.parse_args()

    key = env("TRELLO_KEY")
    token = env("TRELLO_TOKEN")

    with open(args.dataset, "r", encoding="utf-8") as f:
        data = json.load(f)

    for c in data.get("cards", []):
        cid = create_card(c["list_id"], c["name"], c.get("desc", ""), key, token)
        for cl in c.get("checklists", []):
            add_checklist(cid, cl["name"], cl.get("items", []), key, token)
        print(f"OK: {c['name']}")

if __name__ == "__main__":
    main()
