from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.v2.utils.file_utils import get_data_dir, load_json_file
from src.v2.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/analysis/anomalies")
async def get_anomalies():
    """
    Retourne la vue agrégée des anomalies calculées par anomaly_engine_light.

    Source : data/analysis/anomaly_overview.json
    """
    data_dir = Path(get_data_dir())
    anomalies_path = data_dir / "analysis" / "anomaly_overview.json"

    logger.info(
        "[anomalies_route] Lecture de %s",
        anomalies_path,
    )

    data = load_json_file(str(anomalies_path), default=None)

    if not data:
        logger.warning(
            "[anomalies_route] Fichier %s introuvable ou vide",
            anomalies_path,
        )
        raise HTTPException(
            status_code=404,
            detail="anomaly_overview.json introuvable ou vide. "
                   "Assure-toi que anomaly_engine_light a bien été exécuté."
        )

    return data
