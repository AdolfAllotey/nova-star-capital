import os
from datetime import datetime, timezone

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file

logger = get_logger("profitability_tracker")


def _compute_stats(months: list[dict]) -> dict:
    """
    Calcule quelques stats simples sur la rentabilité cumulée.
    Pour l’instant :
    - somme des PnL bruts
    - somme des coûts
    - somme des PnL nets
    - marge nette moyenne
    """
    gross_total = 0.0
    costs_total = 0.0
    net_total = 0.0

    for m in months:
        gross_total += float(m.get("gross_pnl_eur", 0.0))
        costs_total += float(m.get("costs_total_eur", 0.0))
        net_total += float(m.get("net_pnl_eur", 0.0))

    nb = len(months)
    avg_net = net_total / nb if nb else 0.0
    margin_pct = (net_total / gross_total * 100.0) if gross_total != 0 else 0.0

    return {
        "nb_months": nb,
        "gross_total_eur": round(gross_total, 2),
        "costs_total_eur": round(costs_total, 2),
        "net_total_eur": round(net_total, 2),
        "avg_net_per_month_eur": round(avg_net, 2),
        "net_margin_percent": round(margin_pct, 2),
    }


def _find_costs_for_month(costs_months: list[dict], year: int, month: int) -> float:
    """
    Récupère le total des coûts pour un mois donné (si dispo dans monthly_costs.json).
    """
    for c in costs_months:
        if c.get("year") == year and c.get("month") == month:
            return float(c.get("total_eur", 0.0))
    return 0.0


def main() -> None:
    """
    Profitability Tracker – Version light (placeholder V2).

    Objectif :
    - S’assurer qu’un fichier monthly_pnl.json existe pour l’interface Profitability.jsx.
    - Consolider, à minima, les coûts mensuels (monthly_costs.json) avec un PnL brut
      (pour l’instant à 0.0 tant qu’on n’a pas branché les vrais fichiers de PnL).
    - Ne JAMAIS faire planter la boucle quotidienne.

    Évolution future :
    - Lire les PnL mensuels réels (trading, LT, etc.) pour alimenter gross_pnl_eur.
    """

    data_dir = get_data_dir()
    profit_dir = os.path.join(data_dir, "profitability")
    os.makedirs(profit_dir, exist_ok=True)

    pnl_path = os.path.join(profit_dir, "monthly_pnl.json")
    costs_path = os.path.join(data_dir, "costs", "monthly_costs.json")

    logger.info("[profitability_tracker] DATA_DIR=%s, profit_dir=%s", data_dir, profit_dir)

    # Chargement des coûts mensuels (si existants)
    monthly_costs = load_json_file(costs_path, default={"months": []})
    costs_months: list[dict] = monthly_costs.get("months", [])

    # Chargement de l'existant PnL mensuel
    monthly_pnl = load_json_file(
        pnl_path,
        default={
            "stats": {
                "nb_months": 0,
                "gross_total_eur": 0.0,
                "costs_total_eur": 0.0,
                "net_total_eur": 0.0,
                "avg_net_per_month_eur": 0.0,
                "net_margin_percent": 0.0,
            },
            "months": [],
        },
    )

    months: list[dict] = monthly_pnl.get("months", [])

    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month
    label = f"{year:04d}-{month:02d}"

    # Cherche si le mois courant existe déjà dans monthly_pnl.json
    current = None
    for m in months:
        if m.get("year") == year and m.get("month") == month:
            current = m
            break

    # Coûts pour le mois courant (si dispo)
    costs_total_eur = _find_costs_for_month(costs_months, year, month)

    if current is None:
        # Placeholder : gross_pnl encore à 0.0 tant qu’on n’a pas branché les PnL réels
        gross_pnl_eur = 0.0
        net_pnl_eur = gross_pnl_eur - costs_total_eur

        current = {
            "year": year,
            "month": month,
            "label": label,
            # TODO V2+ : alimenter ces champs via les fichiers de résultats de trading
            "gross_pnl_eur": gross_pnl_eur,
            "costs_total_eur": costs_total_eur,
            "net_pnl_eur": net_pnl_eur,
        }
        months.append(current)
        logger.info(
            "[profitability_tracker] Nouveau mois ajouté dans monthly_pnl.json: %s (gross=%.2f, costs=%.2f, net=%.2f)",
            label,
            gross_pnl_eur,
            costs_total_eur,
            net_pnl_eur,
        )
    else:
        # On met simplement à jour la partie coûts/net si les coûts ont changé
        gross_pnl_eur = float(current.get("gross_pnl_eur", 0.0))
        current["costs_total_eur"] = costs_total_eur
        current["net_pnl_eur"] = gross_pnl_eur - costs_total_eur

        logger.info(
            "[profitability_tracker] Mois existant détecté dans monthly_pnl.json: %s (gross=%.2f, costs=%.2f, net=%.2f)",
            label,
            gross_pnl_eur,
            costs_total_eur,
            current["net_pnl_eur"],
        )

    # Recalcule stats globales
    stats = _compute_stats(months)
    monthly_pnl["months"] = months
    monthly_pnl["stats"] = stats

    save_json_file(pnl_path, monthly_pnl)
    logger.info(
        "[profitability_tracker] monthly_pnl.json sauvegardé (%s) – nb_months=%d, net_total_eur=%.2f",
        pnl_path,
        stats["nb_months"],
        stats["net_total_eur"],
    )


if __name__ == "__main__":
    main()
