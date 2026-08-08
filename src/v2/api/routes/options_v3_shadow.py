from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()

BASE = Path("/opt/nsc/data/preprod/options_v3")


def load(name, default=None):
    try:
        p = BASE / name
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def build_payload():
    dashboard = load("options_v3_dashboard.json", {}) or {}
    return {
        "status": load("options_v3_status.json", {}) or {},
        "dashboard": dashboard,
        "signals_validated": load("signals_validated.json", []) or [],
        "signals_rejected": load("signals_rejected.json", []) or [],
        "positions_open": load("options_v3_positions.json", []) or [],
        "positions_closed": load("options_v3_positions_closed.json", []) or [],
        "portfolio_selected": load("options_v3_portfolio_selected.json", []) or [],
        "decisions": load("options_v3_decisions.json", []) or [],
        "kpis": dashboard.get("kpis", {}) if isinstance(dashboard, dict) else {},
        "mode": "SHADOW",
        "execution_allowed": False,
        "real_money_enabled": False,
    }


@router.get("/options/v3/shadow")
def options_v3_shadow():
    return build_payload()


@router.get("/options/v3/shadow/dashboard")
def options_v3_shadow_dashboard():
    return load("options_v3_dashboard.json", {}) or {}


@router.get("/bricks/options/v3/shadow")
def options_v3_brick_shadow():
    return build_payload()
