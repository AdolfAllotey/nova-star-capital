# -*- coding: utf-8 -*-
"""
ico_score.py – calcule hype/risk/score en se basant sur signaux locaux.
Entrée:  data/ico/ico_screened.json + social data (si présents)
Sortie:  data/ico/ico_scored.json
"""
from __future__ import annotations
import os, json, re
from typing import List, Dict, Any
from src.v2.utils.logsafe import get_logger
from src.v2.ico.ico_types import ScoredICO, ScreenedICO, iso_now_utc

log = get_logger("ico_score")
DATA = (
    os.environ.get("NSC_DATA_DIR")
    or os.environ.get("DATA_DIR")
    or os.environ.get("NSC_DATA_ROOT")
    or "/opt/nsc/app/data"
)
IN  = os.path.join(DATA, "ico", "ico_screened.json")
OUT = os.path.join(DATA, "ico", "ico_scored.json")

# Sources sociales (si elles existent)
TG  = os.path.join(DATA, "monitoring", "telegram_data.json")
TW  = os.path.join(DATA, "monitoring", "twitter_data.json")
RD  = os.path.join(DATA, "monitoring", "reddit_data.json")

def load_screened() -> List[ScreenedICO]:
    if not os.path.exists(IN):
        return []
    with open(IN, "r") as f:
        raw = json.load(f)
    out = []
    for x in raw.get("items", []):
        s = ScreenedICO(**x)
        out.append(s)
    return out

def count_mentions(symbol: str, files: List[str]) -> int:
    sym = symbol.upper()
    pat = re.compile(r'\b' + re.escape(sym) + r'\b', re.IGNORECASE)
    count = 0
    for path in files:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # supporter liste directe ou wrapper dict
            messages = data if isinstance(data, list) else data.get("messages") or data.get("items") or []
            for m in messages:
                text = str(m.get("text") or m.get("content") or m.get("title") or "")
                if pat.search(text):
                    count += 1
        except Exception:
            continue
    return count

def calc_features(s: ScreenedICO) -> Dict[str, Any]:
    feats: Dict[str, Any] = {}
    # Hype: normalisation simple par cap
    mentions = count_mentions(s.symbol, [TG, TW, RD])
    hype = min(1.0, mentions / 20.0)  # >=20 mentions -> 1.0
    feats["mentions_48h"] = mentions

    # Risk: pénalités
    risk = 0.3  # base
    if not s.tge_date:
        risk += 0.25
    if not s.website:
        risk += 0.15
    if not s.chain:
        risk += 0.1
    if s.tags and "memecoin" in s.tags:
        risk += 0.1
    risk = max(0.0, min(1.0, risk))

    # Composite
    score = 0.6 * hype + 0.4 * (1.0 - risk)
    return {"hype": round(hype, 4), "risk": round(risk, 4), "score": round(score, 4), **feats}

def main():
    screened = load_screened()
    out: List[ScoredICO] = []
    for s in screened:
        feats = calc_features(s)
        out.append(ScoredICO(**s.__dict__, hype=feats["hype"], risk=feats["risk"], score=feats["score"], features=feats))
    payload = {
        "generated_at": iso_now_utc(),
        "items": [x.__dict__ for x in out],
        "count": len(out),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2)
    log.info("[ICO] scored=%s -> %s", len(out), OUT)

if __name__ == "__main__":
    main()
