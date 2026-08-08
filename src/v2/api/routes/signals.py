from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from datetime import datetime

from src.v2.utils.file_utils import get_data_dir

router = APIRouter()

DATA_DIR = Path(get_data_dir())
AVG_FILE = DATA_DIR / "reports" / "average_sentiment.json"
AVG_FILE_FALLBACK = DATA_DIR / "average_sentiment.json"
MOM_FILE = DATA_DIR / "reports" / "average_momentum.json"
SIG_FILE = DATA_DIR / "reports" / "signals.json"


def _read_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/sentiment", summary="Sentiment & momentum agrégés")
def get_sentiment():
    try:
        data = _read_json(AVG_FILE)
        if not isinstance(data, dict) or not data:
            data = _read_json(AVG_FILE_FALLBACK)

        mom = _read_json(MOM_FILE)
        sig = _read_json(SIG_FILE)

        if not isinstance(data, dict) and not isinstance(sig, dict):
            raise HTTPException(status_code=404, detail="Sentiment indisponible")

        base = data if isinstance(data, dict) else sig

        sentiment = base.get("sentiment") if isinstance(base, dict) else None
        if sentiment is None and isinstance(base, dict):
            sentiment = base.get("overall", base.get("score"))

        momentum = None
        if isinstance(mom, dict):
            momentum = mom.get("momentum", mom.get("value", mom.get("score")))
        if momentum is None and isinstance(base, dict):
            momentum = base.get("momentum")

        date = None
        if isinstance(base, dict):
            date = base.get("date") or base.get("updated_at") or base.get("generated_at")
        if not date:
            date = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        return {
            "sentiment": sentiment,
            "momentum": momentum,
            "score": sentiment,
            "average_sentiment": base,
            "date": date,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture sentiment: {e}")
