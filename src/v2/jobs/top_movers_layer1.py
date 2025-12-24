#!/usr/bin/env python3
"""
Job NSC : filtrer les Top Movers Layer 1 à partir de market/top_movers.json

- Source :  DATA_ROOT/market/top_movers.json
- Cible :   DATA_ROOT/market/top_movers_layer1.json

On garde les mêmes champs que top_movers (price, chg_1h, chg_24h, chg_7d, ...)
mais uniquement pour un sous-ensemble de Layer 1.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List


# --- Config générique ---

DATA_ROOT = Path(os.environ.get("NSC_DATA_ROOT", "/opt/nsc/app/data"))
MARKET_DIR = DATA_ROOT / "market"

SRC = MARKET_DIR / "top_movers.json"
DST = MARKET_DIR / "top_movers_layer1.json"


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    print(f"{ts} [top_movers_layer1] {msg}", flush=True)


# --- Liste des Layer 1 à suivre ---

LAYER1_SYMBOLS = {
    # Majors
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "AVAX",
    "ADA",
    "DOT",
    "ATOM",
    "NEAR",
    "MATIC",
    # Ceux de ton screenshot / focus
    "ZEC",
    "DCR",
    "ICP",
    "FIL",
    # Autres L1 courants
    "OP",   # Optimism (L2 ETH mais infra)
    "ARB",  # Arbitrum
    "SUI",
    "SEI",
    "INJ",
    "TIA",
}


def _load_top_movers() -> List[Dict[str, Any]]:
    """
    Charge market/top_movers.json de façon robuste.

    Formats tolérés :
    - { "updated_at": "...", "items": [ {...}, ... ] }
    - [ {...}, ... ]
    """
    if not SRC.exists():
        log(f"source not found: {SRC}")
        return []

    try:
        raw = json.loads(SRC.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"error reading {SRC}: {e!r}")
        return []

    if isinstance(raw, dict):
        items = raw.get("items") or []
    elif isinstance(raw, list):
        items = raw
    else:
        log("unexpected JSON structure in top_movers.json")
        return []

    if not isinstance(items, list):
        log("items is not a list, abort")
        return []

    return [it for it in items if isinstance(it, dict)]


def _sort_key(it: Dict[str, Any]) -> float:
    """
    Clé de tri : on essaye dans l'ordre chg_30d / p30d / chg_7d / chg_24h.
    Si rien n'est dispo → 0.0
    """
    for key in ("chg_30d", "p30d", "chg_7d", "chg_24h"):
        v = it.get(key)
        if isinstance(v, (int, float)):
            return v
    return 0.0


def main() -> int:
    log(f"DATA_ROOT={DATA_ROOT}")

    items = _load_top_movers()
    if not items:
        log("no items in top_movers.json, nothing to do")
        return 0

    # Filtre L1
    layer1_items: List[Dict[str, Any]] = []
    for it in items:
        sym = str(it.get("symbol") or "").upper()
        if sym in LAYER1_SYMBOLS:
            layer1_items.append(it)

    if not layer1_items:
        log("no Layer1 symbols found in top_movers.json")
    else:
        # Tri décroissant par perf (30j / 7j / 24h)
        layer1_items.sort(key=_sort_key, reverse=True)

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": layer1_items,
    }

    MARKET_DIR.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"wrote {len(layer1_items)} Layer1 movers to {DST}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
