# -*- coding: utf-8 -*-
"""
NSC — Order Selector (Hedge Fund Logic)
--------------------------------------
Décide QUOI trader (sélection portefeuille),
indépendamment de l'exécution et du sizing.
"""

from collections import defaultdict
from typing import List, Dict, Tuple


# ---------------------------------------------------------
# Buckets simples V1 (évolutifs)
# ---------------------------------------------------------
MAJORS = {"btcusdt", "ethusdt"}
L1 = {"solusdt", "avaxusdt", "adausdt", "dotusdt"}
L2 = {"arbusdt", "opusdt", "maticusdt"}
HIGH_BETA = {"dogeusdt", "shibusdt"}


def _bucket_for_symbol(symbol: str) -> str:
    s = symbol.lower()
    if s in MAJORS:
        return "MAJORS"
    if s in L1:
        return "L1"
    if s in L2:
        return "L2"
    if s in HIGH_BETA:
        return "HIGH_BETA"
    return "OTHER"


# ---------------------------------------------------------
# Rank helper (déjà cohérent avec execution_engine)
# ---------------------------------------------------------
def order_rank(o: dict) -> tuple:
    def sf(x, default=-1e9):
        try:
            return float(x)
        except Exception:
            return default

    return (
        sf(o.get("meta_score")),
        sf(o.get("final_score")),
        sf(o.get("score")),
        sf(o.get("requested_weight")),
        sf(o.get("weight")),
    )


# ---------------------------------------------------------
# Sélecteur principal
# ---------------------------------------------------------
def select_orders(
    orders: List[Dict],
    max_orders: int,
    logger=None,
) -> Tuple[List[Dict], Dict]:

    if not isinstance(orders, list) or max_orders <= 0:
        return [], {"reason": "invalid_input"}

    # Rank global
    ranked = sorted(orders, key=order_rank, reverse=True)

    # Quotas hedge-fund style (V1)
    bucket_limits = {
        "MAJORS": 1,
        "L1": 2,
        "L2": 2,
        "HIGH_BETA": 1,
        "OTHER": max_orders,  # fallback
    }

    selected = []
    bucket_count = defaultdict(int)
    dropped = []

    for o in ranked:
        if len(selected) >= max_orders:
            dropped.append({"symbol": o.get("symbol"), "reason": "max_orders"})
            continue

        sym = o.get("symbol")
        if not sym:
            continue

        bucket = _bucket_for_symbol(sym)
        if bucket_count[bucket] >= bucket_limits.get(bucket, 0):
            dropped.append(
                {
                    "symbol": sym,
                    "bucket": bucket,
                    "reason": "bucket_cap",
                }
            )
            continue

        selected.append(o)
        bucket_count[bucket] += 1

    meta = {
        "selected": len(selected),
        "dropped": len(dropped),
        "bucket_count": dict(bucket_count),
        "bucket_limits": bucket_limits,
        "dropped_orders": dropped,
    }

    if logger:
        logger.info(f"[order_selector] selected={len(selected)} dropped={len(dropped)} buckets={dict(bucket_count)}")

    return selected, meta
