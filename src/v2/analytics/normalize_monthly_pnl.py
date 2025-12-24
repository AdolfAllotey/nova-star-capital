# /opt/nsc/src/v2/analytics/normalize_monthly_pnl.py
from __future__ import annotations

import datetime as dt
from decimal import Decimal as D
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

log = get_logger("normalize_monthly_pnl")

ROOT = Path("/opt/nsc")
REPORTS_DIR = ROOT / "src" / "v2" / "data" / "reports"
MONTHLY_PNL_FILE = REPORTS_DIR / "monthly_pnl.json"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _to_float(x: Any) -> float:
    try:
        return float(D(str(x)))
    except Exception:
        return 0.0


def normalize_monthly_pnl() -> Dict[str, Any]:
    """
    Normalise monthly_pnl.json pour s'assurer qu'il a la forme :

    {
      "monthly": [
        {
          "month": "2025-10",
          "pnl_eur": 0.0,
          "costs_eur": 0.0,
          "net_pnl_eur": 0.0,
          "updated_at": "..."
        },
        ...
      ]
    }
    """

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    data = load_json_file(str(MONTHLY_PNL_FILE), default={"monthly": []})
    monthly = data.get("monthly", [])

    if not isinstance(monthly, list):
        log.warning("[normalize] monthly_pnl.json malformed, resetting to empty list")
        monthly = []

    normalized: List[Dict[str, Any]] = []
    seen_months = set()

    for raw in monthly:
        if not isinstance(raw, dict):
            continue

        month = str(raw.get("month", "")).strip()
        if not month:
            continue

        pnl_eur = _to_float(raw.get("pnl_eur", 0.0))
        costs_eur = _to_float(raw.get("costs_eur", raw.get("cost_eur", 0.0)))
        net_pnl_eur = _to_float(
            raw.get("net_pnl_eur", pnl_eur - costs_eur)
        )

        item = {
            "month": month,
            "pnl_eur": pnl_eur,
            "costs_eur": costs_eur,
            "net_pnl_eur": net_pnl_eur,
            "updated_at": raw.get("updated_at", now_utc()),
        }

        # Si le mois existe déjà, on remplace par la dernière version
        if month in seen_months:
            normalized = [m for m in normalized if m["month"] != month]
        seen_months.add(month)
        normalized.append(item)

    # Tri par mois croissant
    normalized.sort(key=lambda x: x["month"])

    payload = {"monthly": normalized}
    save_json_file(str(MONTHLY_PNL_FILE), payload)

    log.info(f"[normalize] monthly entries = {len(normalized)}")
    return {"monthly_len": len(normalized), "file": str(MONTHLY_PNL_FILE)}


if __name__ == "__main__":
    try:
        res = normalize_monthly_pnl()
        print(res)
    except Exception as e:
        log.exception(f"[normalize] error: {e}")
        raise
