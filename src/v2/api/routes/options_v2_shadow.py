from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter(tags=["options-v2-shadow"])

DASHBOARD_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_dashboard.json")

@router.get("/bricks/options/shadow")
def get_options_v2_shadow():
    if not DASHBOARD_PATH.exists():
        return {
            "status": "missing",
            "module": "options_v2_shadow",
            "message": "options_v2_dashboard.json absent"
        }

    try:
        data = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "status": "error",
            "module": "options_v2_shadow",
            "message": str(e)
        }

    kpis = data.get("kpis", {})
    readiness = data.get("readiness", {})
    insights = data.get("insights", {})
    status = data.get("status", {})

    return {
        "status": status.get("pipeline_status", "unknown"),
        "module": "options_v2_shadow",
        "version": status.get("version", "N/A"),
        "mode": status.get("mode", "N/A"),
        "positions_open": kpis.get("positions_open", 0),
        "positions_closed": kpis.get("positions_closed", 0),
        "realized_pnl_eur": kpis.get("realized_pnl_eur", 0),
        "unrealized_pnl_eur": kpis.get("unrealized_pnl_eur", 0),
        "win_rate_pct": kpis.get("win_rate_pct", 0),
        "estimated_risk_open_eur": kpis.get("estimated_risk_open_eur", 0),
        "readiness_score": readiness.get("score", 0),
        "readiness_status": readiness.get("status", "N/A"),
        "top_strategy": insights.get("top_strategy_name", "N/A"),
        "top_ticker": insights.get("top_ticker_name", "N/A"),
        "top_blocker": insights.get("top_blocker_reason", "N/A"),
        "conclusion": data.get("conclusion", "")
    }
