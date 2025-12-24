import os
from datetime import datetime, timezone

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file

logger = get_logger("cost_tracker")


def _compute_stats(months: list[dict]) -> dict:
    """
    Calcule quelques stats simples sur les coûts mensuels.
    Pour l'instant, on ne suit que le total global, mais on pourra
    enrichir ensuite (moyenne, max, etc.).
    """
    total_costs = 0.0
    for m in months:
        total_costs += float(m.get("total_eur", 0.0))

    return {
        "nb_months": len(months),
        "total_costs_eur": round(total_costs, 2),
        "avg_costs_per_month_eur": round(total_costs / len(months), 2) if months else 0.0,
    }


def main() -> None:
    """
    Cost Tracker – Version light (placeholder).

    Objectif principal pour l’instant :
    - Garantir qu’un fichier monthly_costs.json existe,
      avec une structure propre et des coûts à 0.
    - Éviter tout plantage de la boucle quotidienne.

    On enrichira plus tard avec :
    - lecture des coûts OpenAI / Etherscan / infra / etc.
    - consolidation réelle des coûts.
    """

    data_dir = get_data_dir()
    costs_dir = os.path.join(data_dir, "costs")
    os.makedirs(costs_dir, exist_ok=True)
    monthly_path = os.path.join(costs_dir, "monthly_costs.json")

    logger.info("[cost_tracker] DATA_DIR=%s, costs_dir=%s", data_dir, costs_dir)

    # Chargement de l'existant (ou défaut)
    monthly = load_json_file(
        monthly_path,
        default={
            "stats": {
                "nb_months": 0,
                "total_costs_eur": 0.0,
                "avg_costs_per_month_eur": 0.0,
            },
            "months": [],
        },
    )

    months: list[dict] = monthly.get("months", [])
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month
    label = f"{year:04d}-{month:02d}"

    # Recherche d'une entrée pour le mois courant
    current = None
    for m in months:
        if m.get("year") == year and m.get("month") == month:
            current = m
            break

    if current is None:
        # Pour l'instant, on met tous les coûts à 0 –
        # la brique "vraie" mesure de coûts viendra plus tard.
        current = {
            "year": year,
            "month": month,
            "label": label,
            "openai_eur": 0.0,
            "etherscan_eur": 0.0,
            "infra_eur": 0.0,
            "other_eur": 0.0,
            "total_eur": 0.0,
        }
        months.append(current)
        logger.info(
            "[cost_tracker] Nouveau mois ajouté dans monthly_costs.json: %s (total_eur=%.2f)",
            label,
            current["total_eur"],
        )
    else:
        logger.info(
            "[cost_tracker] Mois existant détecté dans monthly_costs.json: %s (total_eur=%.2f)",
            label,
            float(current.get("total_eur", 0.0)),
        )

    # Recalcule des stats globales
    stats = _compute_stats(months)
    monthly["months"] = months
    monthly["stats"] = stats

    save_json_file(monthly_path, monthly)
    logger.info(
        "[cost_tracker] monthly_costs.json sauvegardé (%s) – nb_months=%d, total_costs_eur=%.2f",
        monthly_path,
        stats["nb_months"],
        stats["total_costs_eur"],
    )


if __name__ == "__main__":
    main()
