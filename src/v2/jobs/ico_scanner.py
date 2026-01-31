# -*- coding: utf-8 -*-
"""
ico_scanner.py – agrège des candidats ICO depuis :
1) watchlist_manual.json (local)
2) (optionnel) APIs externes si clés présentes (CMC, etc.)
Écrit: data/ico/ico_candidates.json
"""
from __future__ import annotations
import os, json, datetime as dt
from typing import List, Dict, Any
from src.v2.utils.logsafe import get_logger
from src.v2.ico.ico_types import ICOCandidate, iso_now_utc

log = get_logger("ico_scanner")

DATA = (
    os.environ.get("NSC_DATA_DIR")
    or os.environ.get("DATA_DIR")
    or os.environ.get("NSC_DATA_ROOT")
    or "/opt/nsc/app/data"
)
OUT = os.path.join(DATA, "ico", "ico_candidates.json")
MANUAL = os.path.join(DATA, "ico", "watchlist_manual.json")

def load_manual() -> List[ICOCandidate]:
    items: List[ICOCandidate] = []
    if not os.path.exists(MANUAL):
        log.warning("watchlist_manual.json introuvable: %s", MANUAL)
        return items
    try:
        with open(MANUAL, "r") as f:
            payload = json.load(f)
        for raw in payload.get("items", []):
            c = ICOCandidate(
                symbol=raw.get("symbol",""),
                name=raw.get("name",""),
                chain=raw.get("chain"),
                tge_date=raw.get("tge_date"),
                website=raw.get("website"),
                tags=raw.get("tags"),
                source="manual",
                notes=raw.get("notes"),
                raw=raw,
            )
            c.normalize()
            if c.symbol and c.name:
                items.append(c)
    except Exception as e:
        log.exception("Erreur lecture watchlist manual: %s", e)
    return items

# Connecteur optionnel CoinMarketCap (requiert CMC_API_KEY)
def fetch_cmc_upcoming() -> List[ICOCandidate]:
    import requests
    key = os.environ.get("CMC_API_KEY")
    if not key:
        return []
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/airdrop"  # proxy évènementiel
    # NB: CMC n’expose pas un vrai endpoint public ‘ICO upcoming’ stable.
    # On garde ce connecteur comme bonus: il peut renvoyer vide.
    try:
        r = requests.get(url, headers={"X-CMC_PRO_API_KEY": key, "Accept":"application/json"}, timeout=10)
        if r.status_code != 200:
            log.warning("CMC %s -> %s", url, r.status_code)
            return []
        data = r.json()
        out: List[ICOCandidate] = []
        for x in data.get("data", []):
            sym = x.get("symbol") or ""
            name = x.get("name") or ""
            if not sym or not name:
                continue
            c = ICOCandidate(
                symbol=sym,
                name=name,
                chain=None,
                tge_date=None,
                website=None,
                tags=["cmc-airdrop"],
                source="cmc",
                raw=x,
            )
            c.normalize()
            out.append(c)
        return out
    except Exception as e:
        log.warning("CMC fetch error: %s", e)
        return []

def dedupe(cands: List[ICOCandidate]) -> List[ICOCandidate]:
    seen = set()
    out: List[ICOCandidate] = []
    for c in cands:
        k = (c.symbol, c.name.lower())
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out

def main():
    all_items: List[ICOCandidate] = []

    # 1) Local manual
    all_items.extend(load_manual())

    # 2) Optionnel: CMC si clé
    all_items.extend(fetch_cmc_upcoming())

    # Dédupe
    all_items = dedupe(all_items)

    payload: Dict[str, Any] = {
        "generated_at": iso_now_utc(),
        "items": [c.to_dict() for c in all_items],
        "count": len(all_items),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"items": [x.to_dict() if hasattr(x, "to_dict") else (x.__dict__ if hasattr(x, "__dict__") else x) for x in all_items], "updated_at": iso_now_utc()}, f, indent=2)
    log.info("[ICO] wrote %s items -> %s", len(all_items), OUT)

if __name__ == "__main__":
    main()
