# -*- coding: utf-8 -*-
"""
ico_screener.py – applique des filtres (date TGE valide, symbol/name non vides, doublons)
Entrée:  data/ico/ico_candidates.json
Sortie:  data/ico/ico_screened.json
"""
from __future__ import annotations
import os, json
from typing import List, Dict, Any
from src.v2.utils.logsafe import get_logger
from src.v2.ico.ico_types import ICOCandidate, ScreenedICO, safe_date, iso_now_utc

log = get_logger("ico_screener")
DATA = (
    os.environ.get("NSC_DATA_DIR")
    or os.environ.get("DATA_DIR")
    or os.environ.get("NSC_DATA_ROOT")
    or "/opt/nsc/app/data"
)
IN  = os.path.join(DATA, "ico", "ico_candidates.json")
OUT = os.path.join(DATA, "ico", "ico_screened.json")

def load_candidates() -> List[ICOCandidate]:
    if not os.path.exists(IN):
        return []
    with open(IN, "r") as f:
        raw = json.load(f)
    items = []
    for x in raw.get("items", []):
        c = ICOCandidate(**{k:x.get(k) for k in [
            "symbol","name","chain","tge_date","website","tags","source","notes","raw"
        ]})
        c.normalize()
        items.append(c)
    return items

def screen(items: List[ICOCandidate]) -> List[ScreenedICO]:
    out: List[ScreenedICO] = []
    for c in items:
        reasons = []
        valid = True
        if not c.symbol or not c.name:
            valid = False; reasons.append("missing_symbol_or_name")
        if c.tge_date and not safe_date(c.tge_date):
            valid = False; reasons.append("invalid_tge_date")
        out.append(ScreenedICO(**c.to_dict(), valid=valid, reasons=reasons or None))
    # ne garde que valid=True
    return [x for x in out if x.valid]

def main():
    items = load_candidates()
    scr = screen(items)
    payload: Dict[str, Any] = {
        "generated_at": iso_now_utc(),
        "items": [x.__dict__ for x in scr],
        "count": len(scr),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2)
    log.info("[ICO] screened=%s -> %s", len(scr), OUT)

if __name__ == "__main__":
    main()
