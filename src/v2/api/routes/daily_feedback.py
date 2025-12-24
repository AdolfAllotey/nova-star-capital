from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# On remonte jusqu'à /opt/nsc/app
# /opt/nsc/app/src/v2/api/routes/daily_feedback.py
# parents[0] = routes
# parents[1] = api
# parents[2] = v2
# parents[3] = src
# parents[4] = app   ✅
ROOT_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT_DIR / "data"
DAILY_FEEDBACK_PATH = DATA_DIR / "analysis" / "daily_feedback.json"


@router.get("/daily-feedback")
def get_daily_feedback():
    """
    Retourne le feedback quotidien calculé par daily_trading_feedback.py
    """
    logger.info("[daily_feedback] Route /analysis/daily-feedback appelée")
    logger.info("[daily_feedback] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR)
    logger.info("[daily_feedback] DAILY_FEEDBACK_PATH=%s", DAILY_FEEDBACK_PATH)

    if not DAILY_FEEDBACK_PATH.exists():
        logger.warning(
            "[daily_feedback] Fichier introuvable: %s", DAILY_FEEDBACK_PATH
        )
        raise HTTPException(
            status_code=404,
            detail=f"daily_feedback.json introuvable ({DAILY_FEEDBACK_PATH})",
        )

    try:
        with DAILY_FEEDBACK_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # pragma: no cover
        logger.exception(
            "[daily_feedback] Erreur de lecture du fichier %s: %s",
            DAILY_FEEDBACK_PATH,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la lecture de daily_feedback.json",
        )

    # Petit garde-fou : si ce n'est pas un dict, on emballe
    if not isinstance(data, dict):
        logger.warning(
            "[daily_feedback] Contenu inattendu dans daily_feedback.json (type=%s), encapsulation dans un dict.",
            type(data),
        )
        data = {"raw": data}

    return JSONResponse(content=data)
