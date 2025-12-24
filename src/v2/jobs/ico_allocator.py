# -*- coding: utf-8 -*-
"""
ico_allocator.py – propose une allocation $ par candidat selon le score & régime.
Entrée:  data/ico/ico_scored.json + analysis/market_regime.json (optionnel)
Sortie:  data/ico/ico_allocation.json
"""
from __future__ import annotations
import os, json
from typing import List, Dict, Any
from src.v2.utils.logsafe import get_logger
from src.v2.ico.ico_types import Allocation, AllocationPlan, iso_now_utc

log = get_logger("ico_allocator")
DATA = (
    os.environ.get("NSC_DATA_DIR")
    or os.environ.get("DATA_DIR")
    or os.environ.get("NSC_DATA_ROOT")
    or "/opt/nsc/app/data"
)
IN   = os.path.join(DATA, "ico", "ico_scored.json")
REG  = os.path.join(DATA, "analysis", "market_regime.json")
OUT  = os.path.join(DATA, "ico", "ico_allocation.json")

def load_scored():
    if not os.path.exists(IN):
        return []
    with open(IN, "r") as f:
        raw = json.load(f)
    return raw.get("items", [])

def load_regime() -> str:
    if not os.path.exists(REG):
        return "neutral"
    try:
        with open(REG,"r") as f:
            r = json.load(f)
        return r.get("regime") or "neutral"
    except Exception:
        return "neutral"

def main():
    scored = load_scored()
    regime = load_regime()

    # Budget base (env) modifié par régime
    base = float(os.environ.get("NSC_ICO_BUDGET_USD", "3000"))
    mult = {"bull": 1.0, "neutral": 0.7, "bear": 0.4}.get(regime, 0.7)
    budget = base * mult

    # Pondération par score (>=0.5)
    cand = [x for x in scored if (x.get("score") or 0) >= 0.50]
    ssum = sum([x["score"] for x in cand]) or 1.0

    # garde-fous
    cap_min = float(os.environ.get("NSC_ICO_MIN_TICKET", "150"))
    cap_max = float(os.environ.get("NSC_ICO_MAX_TICKET", "1000"))

    items: List[Allocation] = []
    for x in cand:
        w = (x["score"] / ssum)
        amt = max(cap_min, min(cap_max, budget * w))
        items.append(Allocation(symbol=x["symbol"], amount_usd=round(amt,2),
                                rationale=f"score={x['score']}, regime={regime}"))

    plan = AllocationPlan(generated_at=iso_now_utc(), regime=regime, budget_usd=budget, items=items)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(plan.to_dict(), f, indent=2)
    log.info("[ICO] allocation %s -> %s", len(items), OUT)

if __name__ == "__main__":
    main()
