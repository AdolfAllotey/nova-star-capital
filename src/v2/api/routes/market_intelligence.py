from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter()

BASE = Path("/opt/nsc/data/preprod")
APP_BASE = Path("/opt/nsc/app/data/preprod")

def read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def read_brief_history(limit: int = 20):
    hist = BASE / "market_brief/history"
    items = []
    try:
        for f in sorted(hist.glob("executive_market_brief_*.json"), reverse=True)[:limit]:
            data = read_json(f, {})
            if data:
                items.append(data)
    except Exception:
        pass
    return items


@router.get("/api/market-intelligence")
def market_intelligence():
    return {
        "top_movers": read_json(BASE / "market/top_movers_combined.json", {}),
        "discovery_summary": read_json(BASE / "discovery/discovery_summary.json", {}),
        "meta_rankings": read_json(BASE / "discovery/meta_rankings.json", {}),
        "meta_validation": read_json(BASE / "discovery/meta_validation.json", {}),
        "activity_dashboard": read_json(APP_BASE / "activity/activity_dashboard.json", {}),
        "executive_market_brief": read_json(BASE / "market_brief/executive_market_brief.json", {}),
        "executive_market_brief_history": read_brief_history(20),
    }
