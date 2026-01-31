import os
import json
from datetime import datetime, timezone, timezone
from src.v2.utils.logger import get_logger

logger = get_logger("dashboard_generator")

# Chemins d'entrée
SIMULATION_RESULTS_PATH = "data/simulation/simulation_results.json"
CUMULATIVE_RESULTS_PATH = "data/simulation/cumulative_results.json"
WORST_SUMMARY_PATH = "data/risk/worst_trades_summary.json"
BLACKLIST_PATH = "data/risk/token_blacklist.json"

# Chemin de sortie
DASHBOARD_OUTPUT_PATH = "data/reports/dashboard_data.json"

def load_json(path):
    if not os.path.exists(path):
        logger.warning(f"Fichier non trouvé : {path}")
        return None
    with open(path, "r") as f:
        return json.load(f)

def generate_dashboard_data():
    simulation = load_json(SIMULATION_RESULTS_PATH)
    cumulative = load_json(CUMULATIVE_RESULTS_PATH)
    worst_summary = load_json(WORST_SUMMARY_PATH)
    blacklist = load_json(BLACKLIST_PATH)

    if not simulation or not cumulative:
        logger.error("Impossible de générer le dashboard : données manquantes.")
        return

    dashboard = {
        "date": simulation.get("date"),
        "daily_results": simulation.get("results", []),
        "daily_pnl": cumulative.get("history", [{}])[-1].get("daily_pnl", 0),
        "total_pnl": cumulative.get("total_pnl", 0),
        "summary": worst_summary.get("summary", "") if worst_summary else "",
        "blacklist": blacklist.get("blacklisted_tokens", []) if blacklist else [],
        "status_distribution": {},
        "top_performers": [],
        "worst_performers": [],
    }

    # Répartition par statut
    status_count = {}
    for trade in dashboard["daily_results"]:
        status = trade.get("status", "UNKNOWN")
        status_count[status] = status_count.get(status, 0) + 1
    dashboard["status_distribution"] = status_count

    # Top et worst performers
    sorted_results = sorted(dashboard["daily_results"], key=lambda x: x["pnl"], reverse=True)
    dashboard["top_performers"] = sorted_results[:5]
    dashboard["worst_performers"] = sorted_results[-5:]

    # Sauvegarde
    os.makedirs(os.path.dirname(DASHBOARD_OUTPUT_PATH), exist_ok=True)
    with open(DASHBOARD_OUTPUT_PATH, "w") as f:
        json.dump(dashboard, f, indent=2)

    logger.info(f"Dashboard généré avec succès pour {dashboard['date']}.")

if __name__ == "__main__":
    generate_dashboard_data()