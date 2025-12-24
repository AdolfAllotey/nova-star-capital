# /opt/nsc/src/v2/analytics/generate_monthly_pnl.py
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

log = get_logger("generate_monthly_pnl")

# --- Paths -----------------------------------------------------------------------
ROOT = Path("/opt/nsc")
DATA_DIR = ROOT / "src" / "v2" / "data"
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MONTHLY_PNL_FILE = REPORTS_DIR / "monthly_pnl.json"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_monthly_doc() -> Dict[str, Any]:
    """
    Charge monthly_pnl.json et normalise la structure :
    {
      "monthly": [
        { "month": "YYYY-MM", "pnl_eur": float, "updated_at": str, ... },
        ...
      ]
    }
    """
    doc = load_json_file(str(MONTHLY_PNL_FILE), default={})
    if not isinstance(doc, dict):
        doc = {}

    monthly = doc.get("monthly")
    if not isinstance(monthly, list):
        monthly = []
    doc["monthly"] = monthly
    return doc


def ensure_current_month_entry(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    S'assure qu'il existe au moins UNE entrée pour le mois courant.
    Si aucune entrée pour le mois YYYY-MM courant -> en crée une avec pnl_eur = 0.0.
    """
    today = dt.date.today()
    current_month = today.strftime("%Y-%m")

    monthly: List[Dict[str, Any]] = doc.get("monthly", [])

    # Cherche si le mois courant existe déjà
    existing = None
    for row in monthly:
        if str(row.get("month")) == current_month:
            existing = row
            break

    if existing is None:
        # Création d'une nouvelle entrée "neutre"
        row = {
            "month": current_month,
            "pnl_eur": 0.0,
            "updated_at": now_utc(),
        }
        monthly.append(row)
        log.info(f"[monthly_pnl] created new month row → {row}")
    else:
        # On met juste à jour le timestamp (au cas où)
        existing["updated_at"] = now_utc()
        log.info(f"[monthly_pnl] updated existing month row → {existing}")

    # Trie éventuellement par mois croissant (optionnel)
    monthly.sort(key=lambda r: str(r.get("month")))
    doc["monthly"] = monthly
    return doc


def main() -> None:
    """
    Entrée principale :
    - charge monthly_pnl.json
    - garantit une entrée pour le mois courant (pnl_eur=0 si rien)
    - sauvegarde le fichier
    - imprime un petit résumé JSON
    """
    log.info(f"[monthly_pnl] start, file={MONTHLY_PNL_FILE}")

    doc = load_monthly_doc()
    doc = ensure_current_month_entry(doc)

    save_json_file(str(MONTHLY_PNL_FILE), doc)
    log.info(f"[monthly_pnl] saved {MONTHLY_PNL_FILE}")

    # Retour console (utile pour systemd/journalctl ou exécution manuelle)
    current_month = dt.date.today().strftime("%Y-%m")
    current = [r for r in doc["monthly"] if r.get("month") == current_month][0]

    print(
        json.dumps(
            {
                "status": "ok",
                "file": str(MONTHLY_PNL_FILE),
                "updated": current,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.exception(f"[monthly_pnl] error: {e}")
        print(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False))
        raise
