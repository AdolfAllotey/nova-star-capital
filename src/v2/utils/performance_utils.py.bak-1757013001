import json
import os
from src.v2.utils.logger import get_logger

logger = get_logger("performance_utils")

PERF_FILE = "data/simulation/global_performance.json"

def get_global_perf() -> float:
    """
    Récupère la performance globale cumulée du bot (depuis le début).
    """
    try:
        if not os.path.exists(PERF_FILE):
            logger.warning("Fichier de performance global introuvable.")
            return 0.0

        with open(PERF_FILE, "r") as f:
            data = json.load(f)
            return float(data.get("global_perf", 0.0))

    except Exception as e:
        logger.exception(f"Erreur de lecture de {PERF_FILE}")
        return 0.0

def update_global_perf(new_perf: float):
    """
    Met à jour le fichier de performance globale.
    """
    try:
        os.makedirs(os.path.dirname(PERF_FILE), exist_ok=True)
        with open(PERF_FILE, "w") as f:
            json.dump({"global_perf": round(new_perf, 4)}, f)
        logger.info(f"Perf globale mise à jour : {new_perf:.2%}")
    except Exception as e:
        logger.exception(f"Erreur de mise à jour de {PERF_FILE}")