#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import json, os, time
from typing import Any, Dict

TAX_RATE = 0.25
THRESHOLD_EUR = 10_000.0
POST10K_WEIGHTS = {
    "reinject_bot": 0.50,
    "long_term_crypto": 0.20,
    "securite": 0.10,
    "entreprise": 0.10,
    "bfr": 0.10,
}
RUNTIME_FILE = "/root/src/v2/data/runtime/allocator_last.json"

def _now_utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _ensure_dir(p: str) -> None:
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

def allocate(*, balance: float | None = None, profit: float | None = None,
             bot_pct: float | None = None, bench_pct: float | None = None,
             **kwargs) -> Dict[str, Any]:
    """Calcule la répartition selon les règles NSC (impôts 25%, seuil 10k, etc.)."""
    balance = float(balance) if balance is not None else None
    profit  = float(profit)  if profit  is not None else None

    # Valeurs par défaut si non fournies (on neutralise)
    if profit is None:
        profit = 0.0

    splits = {
        "impots": 0.0,
        "reinject_bot": 0.0,
        "long_term_crypto": 0.0,
        "securite": 0.0,
        "entreprise": 0.0,
        "bfr": 0.0,
        "metals_pending": 0.0,
        "lt_actions_pending": 0.0,
    }
    journal = []

    # Cas 1: pas de profit
    if profit <= 0:
        result = {
            "status": "no_profit",
            "splits": splits,
            "reinject_ok": False,
            "journal": journal,
            "context": {
                "balance": balance,
                "profit": profit,
                "tax_rate": TAX_RATE,
                "threshold_eur": THRESHOLD_EUR,
                "post10k_weights": POST10K_WEIGHTS,
            },
        }
        _write_runtime(result)
        return result

    # Isoler les impôts
    impots = round(profit * TAX_RATE, 2)
    splits["impots"] = impots
    journal.append({
        "id": time.strftime("%Y%m%d%H%M%S", time.gmtime()) + "01",
        "ts": _now_utc_iso(),
        "src": "exchange_profit",
        "dst": "impots",
        "amount_eur": impots,
        "meta": {"note": "isolation impots"},
    })

    reste = round(profit - impots, 2)

    # Cas 2: sous le seuil → on garde seulement impôts
    if (balance or 0.0) < THRESHOLD_EUR:
        result = {
            "status": "below_threshold",
            "splits": splits,
            "reinject_ok": False,
            "journal": journal,
            "context": {
                "balance": balance,
                "profit": profit,
                "tax_rate": TAX_RATE,
                "threshold_eur": THRESHOLD_EUR,
                "post10k_weights": POST10K_WEIGHTS,
            },
        }
        _write_runtime(result)
        return result

    # Cas 3: au-dessus du seuil → répartir le reste
    for key, w in POST10K_WEIGHTS.items():
        amt = round(reste * w, 2)
        splits[key] = amt
        journal.append({
            "id": time.strftime("%Y%m%d%H%M%S", time.gmtime()) + f"{int(w*100):02d}",
            "ts": _now_utc_iso(),
            "src": "exchange_profit",
            "dst": key,
            "amount_eur": amt,
            "meta": {"weight": w},
        })

    result = {
        "status": "allocated",
        "splits": splits,
        "reinject_ok": True,
        "journal": journal,
        "context": {
            "balance": balance,
            "profit": profit,
            "tax_rate": TAX_RATE,
            "threshold_eur": THRESHOLD_EUR,
            "post10k_weights": POST10K_WEIGHTS,
        },
    }
    _write_runtime(result)
    return result

def _write_runtime(payload: Dict[str, Any]) -> None:
    payload = dict(payload)
    payload["runtime_file"] = RUNTIME_FILE
    _ensure_dir(RUNTIME_FILE)
    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# Optionnel: exécution directe pour debug rapide
if __name__ == "__main__":
    # Petit test: balance 12k, profit 2k
    out = allocate(balance=12000, profit=2000)
    print(json.dumps(out, ensure_ascii=False))
