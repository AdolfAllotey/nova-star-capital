from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter()
BASE = Path("/opt/nsc/data/preprod/executive_decision")

def read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def read_history(limit: int = 20):
    hist = BASE / "history"
    items = []
    try:
        for f in sorted(hist.glob("executive_decision_*.json"), reverse=True)[:limit]:
            data = read_json(f, {})
            if data:
                items.append(data)
    except Exception:
        pass
    return items


@router.get("/api/executive-decision")
def executive_decision():
    current = read_json(BASE / "executive_decision.json", {
        "status": "empty",
        "decision": "UNKNOWN",
        "waterfall": [],
        "drivers": [],
        "rejections": [],
    })
    current["history"] = read_history(20)
    return current
