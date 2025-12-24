# /root/src/v2/transfers.py
from __future__ import annotations
import json, os, csv
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, List, Tuple

RUNTIME_DIR = Path("/root/src/v2/data/runtime")
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

# Mapping par défaut (override possible via NSC_ACCOUNT_MAP en JSON)
DEFAULT_ACCOUNT_MAP = {
    "impots":           "Taxes (Impots)",
    "reinject_bot":     "Bot (Reinject)",
    "long_term_crypto": "LT Crypto",
    "securite":         "Sécurité",
    "entreprise":       "Entreprise",
    "bfr":              "BFR",
    # poches “placeholder”
    "metals_pending":   "Metals (Pending)",
    "lt_actions_pending":"LT Actions (Pending)",
}

def _load_account_map() -> Dict[str, str]:
    raw = os.getenv("NSC_ACCOUNT_MAP", "").strip()
    if not raw:
        return DEFAULT_ACCOUNT_MAP
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("NSC_ACCOUNT_MAP doit être un objet JSON")
        merged = DEFAULT_ACCOUNT_MAP.copy()
        merged.update({str(k): str(v) for k, v in data.items()})
        return merged
    except Exception as e:
        print(f"[transfers][WARN] NSC_ACCOUNT_MAP invalide: {e} — on utilise le mapping par défaut")
        return DEFAULT_ACCOUNT_MAP

def _flatten_journal(journal: List[Dict[str, Any]]) -> Dict[str, float]:
    """ Agrège les montants par 'dst' à partir du journal allocator. """
    agg: Dict[str, float] = {}
    for line in journal or []:
        dst = line.get("dst")
        amt = float(line.get("amount_eur", 0.0) or 0.0)
        if not dst or amt <= 0:
            continue
        agg[dst] = agg.get(dst, 0.0) + amt
    return agg

def plan_from_allocator(alloc: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convertit la sortie allocator (dict) en plan de transferts.
    Retourne (rows, meta) :
      rows = [{pocket, account, amount_eur}]
      meta = {status, total, by_pocket}
    """
    status = str(alloc.get("status", "unknown"))
    journal = alloc.get("journal") or []
    by_pocket = _flatten_journal(journal)
    account_map = _load_account_map()

    rows: List[Dict[str, Any]] = []
    total = 0.0
    for pocket, amount in sorted(by_pocket.items()):
        if amount <= 0:
            continue
        account = account_map.get(pocket, pocket)
        rows.append({
            "pocket": pocket,
            "account": account,
            "amount_eur": round(float(amount), 2),
        })
        total += float(amount)

    meta = {
        "status": status,
        "total_eur": round(total, 2),
        "by_pocket": {k: round(float(v), 2) for k, v in by_pocket.items()},
        "account_map": account_map,
    }
    return rows, meta

def save_plan(rows: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, str]:
    """ Sauvegarde JSON + CSV dans v2/data/runtime/ ; renvoie les chemins. """
    out_json = RUNTIME_DIR / "transfers_last.json"
    out_csv  = RUNTIME_DIR / "transfers_last.csv"

    payload = {"meta": meta, "transfers": rows}
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pocket", "account", "amount_eur"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    return {"json": str(out_json), "csv": str(out_csv)}

def summarize(rows: List[Dict[str, Any]], meta: Dict[str, Any]) -> str:
    if not rows:
        return "[transfers] Aucun transfert à planifier."
    parts = [f"[transfers] Plan ({meta.get('status')}), total ≈ {meta.get('total_eur')}€:"]
    for r in rows:
        parts.append(f" - {r['account']}  ←  {r['amount_eur']}€  (poche: {r['pocket']})")
    return "\n".join(parts)
