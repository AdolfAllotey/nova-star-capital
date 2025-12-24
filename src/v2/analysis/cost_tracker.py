from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)


def _parse_timestamp(ts: str) -> Tuple[int, int]:
    """
    Parse un timestamp ISO ou proche ISO et renvoie (year, month).
    Si parsing impossible, on remonte ValueError.
    """
    # On gère quelques formats simples
    for fmt in ("%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d"):
        try:
            dt = datetime.strptime(ts, fmt)
            return dt.year, dt.month
        except Exception:
            continue
    # Tentative fromisoformat (Python 3.11+ ok)
    try:
        dt = datetime.fromisoformat(ts)
        return dt.year, dt.month
    except Exception as exc:
        raise ValueError(f"Impossible de parser le timestamp: {ts}") from exc


def _load_cost_events(path: Path) -> List[Dict[str, Any]]:
    """
    Charge un fichier JSONL d'événements de coûts.
    Chaque ligne doit être un JSON du type:
      {
        "timestamp": "2025-12-07T10:15:00Z",
        "category": "openai",
        "provider": "OpenAI",
        "amount_eur": 0.12,
        "meta": {...}
      }
    """
    if not path.exists():
        logger.warning(
            "[cost_tracker] Aucun fichier de coûts trouvé (%s). Retour liste vide.",
            path,
        )
        return []

    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    logger.warning(
                        "[cost_tracker] Ligne %d: objet non dict -> ignoré.",
                        line_no,
                    )
                    continue
                events.append(obj)
            except json.JSONDecodeError:
                logger.warning(
                    "[cost_tracker] Ligne %d: JSON invalide -> ignoré.",
                    line_no,
                )
                continue

    logger.info(
        "[cost_tracker] %d événements de coûts chargés depuis %s",
        len(events),
        path,
    )
    return events


def _aggregate_monthly_costs(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agrège les coûts par mois et par catégorie.
    Retourne une structure:
    {
      "stats": {...},
      "months": [
         {
           "year": 2025,
           "month": 12,
           "label": "2025-12",
           "total_eur": 123.45,
           "categories": {
             "openai": 50.0,
             "servers": 70.0,
             ...
           }
         },
         ...
      ]
    }
    """
    monthly: Dict[str, Dict[str, Any]] = {}

    for ev in events:
        ts = ev.get("timestamp")
        if not ts:
            logger.warning("[cost_tracker] Événement sans timestamp: %s", ev)
            continue

        try:
            year, month = _parse_timestamp(ts)
        except ValueError:
            logger.warning("[cost_tracker] Timestamp invalide: %s", ts)
            continue

        key = f"{year:04d}-{month:02d}"
        amount = ev.get("amount_eur", 0.0)
        try:
            amount = float(amount)
        except Exception:
            logger.warning(
                "[cost_tracker] amount_eur invalide pour %s: %r -> ignoré",
                key,
                amount,
            )
            continue

        category = str(ev.get("category") or "unknown")

        if key not in monthly:
            monthly[key] = {
                "year": year,
                "month": month,
                "label": key,
                "total_eur": 0.0,
                "categories": {},
            }

        m = monthly[key]
        m["total_eur"] += amount
        m["categories"][category] = m["categories"].get(category, 0.0) + amount

    # Tri par (year, month)
    months_list = sorted(
        monthly.values(),
        key=lambda x: (x["year"], x["month"]),
    )

    total_cost = sum(m["total_eur"] for m in months_list)
    nb_months = len(months_list)
    avg_per_month = total_cost / nb_months if nb_months > 0 else 0.0

    stats = {
        "nb_events": len(events),
        "nb_months": nb_months,
        "total_cost_eur": total_cost,
        "avg_cost_per_month_eur": avg_per_month,
        "last_month": months_list[-1]["label"] if months_list else None,
    }

    return {
        "stats": stats,
        "months": months_list,
    }


def main() -> None:
    data_dir = Path(os.getenv("NSC_DATA_DIR", "data")).resolve()
    costs_dir = data_dir / "costs"
    costs_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[cost_tracker] DATA_DIR=%s, costs_dir=%s", data_dir, costs_dir)

    events_path = costs_dir / "cost_events.jsonl"
    monthly_costs_path = costs_dir / "monthly_costs.json"

    events = _load_cost_events(events_path)
    agg = _aggregate_monthly_costs(events)

    save_json_file(monthly_costs_path, agg)
    logger.info(
        "[cost_tracker] monthly_costs.json sauvegardé (%s) – nb_months=%d, total_cost=%.2f",
        monthly_costs_path,
        agg["stats"]["nb_months"],
        agg["stats"]["total_cost_eur"],
    )

    # Éventuel fichier de compatibilité à la racine
    root_monthly_costs = data_dir / "monthly_costs.json"
    save_json_file(root_monthly_costs, agg)
    logger.info(
        "[cost_tracker] Copie de monthly_costs.json sauvegardée à la racine (%s).",
        root_monthly_costs,
    )


if __name__ == "__main__":
    main()
