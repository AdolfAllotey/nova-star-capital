from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter()

PAM_PATH = Path("/opt/nsc/app/data/preprod/activity/activity_dashboard.json")

@router.get("/activity-dashboard")
def get_activity_dashboard():
    if not PAM_PATH.exists():
        return {"status": "missing", "summary": {}, "engines": [], "alerts": []}
    try:
        return json.loads(PAM_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "error", "error": str(e), "summary": {}, "engines": [], "alerts": []}
