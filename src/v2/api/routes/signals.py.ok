from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from datetime import datetime

router = APIRouter()  # pas de prefix ici

# /opt/nsc/app/src/v2/api/routes/signals.py -> parents[2] == ".../src/v2"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
AVG_FILE = DATA_DIR / "reports" / "average_sentiment.json"
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
        if not isinstance(data, dict) or ("sentiment" not in data and "momentum" not in data):
            data = _read_json(SIG_FILE)

        if not isinstance(data, dict) or ("sentiment" not in data and "momentum" not in data):
            raise HTTPException(status_code=404, detail="Sentiment indisponible")

        sentiment = data.get("sentiment")
        momentum = data.get("momentum")
        date = data.get("date") or data.get("updated_at") or datetime.utcnow().isoformat()

        return {
            "sentiment": sentiment,
            "momentum": momentum,
            "date": date,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture sentiment: {e}")
