"""
NSC Equity Curve Engine
Appends a simple performance history for Executive / dashboards.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ANALYSIS_DIR = Path("/opt/nsc/data/preprod/analysis")
PNL_STATE_PATH = ANALYSIS_DIR / "pnl_state.json"
OPTIONS_V2_DAILY_REPORT_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_daily_report.json")
CAPITAL_ALLOCATOR_STATE_PATH = ANALYSIS_DIR / "capital_allocator_state.json"
PORTFOLIO_STATE_PATH = Path("/opt/nsc/data/preprod/portfolio/state/portfolio_state.json")
OUTPUT_PATH = ANALYSIS_DIR / "equity_curve_state.json"
DASHBOARD_V3_URL = "http://127.0.0.1:8000/dashboard/v3"

MAX_POINTS = 2500000


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default=None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default



def get_dashboard_global_pnl():
    try:
        with urllib.request.urlopen(DASHBOARD_V3_URL, timeout=2) as r:
            payload = json.loads(r.read().decode("utf-8"))
        g = payload.get("global", {}) if isinstance(payload, dict) else {}

        active = float(g.get("pnlGlobal", 0.0) or 0.0)
        shadow = float(g.get("pnlShadow", 0.0) or 0.0)
        total_including_shadow = float(g.get("pnlTotalIncludingShadow", active + shadow) or 0.0)

        strategies = payload.get("strategies", []) if isinstance(payload, dict) else []
        realized_active = 0.0
        unrealized_active = 0.0

        if isinstance(strategies, list):
            for s in strategies:
                if not isinstance(s, dict):
                    continue

                mode = str(s.get("mode", "") or "").upper()
                if mode == "SHADOW":
                    continue

                try:
                    realized_active += float(s.get("realizedPnl", 0.0) or 0.0)
                except Exception:
                    pass

                try:
                    unrealized_active += float(s.get("unrealizedPnl", 0.0) or 0.0)
                except Exception:
                    pass

        return {
            "active": active,
            "shadow": shadow,
            "total_including_shadow": total_including_shadow,
            "realized_active": realized_active,
            "unrealized_active": unrealized_active,
        }
    except Exception:
        return None

def build_equity_curve_state() -> dict:
    pnl_state = load_json(PNL_STATE_PATH, {}) or {}
    allocator_state = load_json(CAPITAL_ALLOCATOR_STATE_PATH, {}) or {}
    portfolio_state = load_json(PORTFOLIO_STATE_PATH, {}) or {}
    existing = load_json(OUTPUT_PATH, {}) or {}

    pnl = pnl_state.get("summary", {}) if isinstance(pnl_state, dict) else {}
    totals = allocator_state.get("totals", {}) if isinstance(allocator_state, dict) else {}

    options_v2 = load_json(OPTIONS_V2_DAILY_REPORT_PATH, {}) or {}
    options_perf = options_v2.get("performance", {}) if isinstance(options_v2, dict) else {}

    crypto_total = float(pnl.get("total_pnl_eur", 0.0) or 0.0)
    crypto_realized = float(pnl.get("realized_pnl_eur", 0.0) or 0.0)
    options_realized = float(options_perf.get("realized_pnl_eur", 0.0) or 0.0)
    options_unrealized = float(options_perf.get("unrealized_pnl_eur", 0.0) or 0.0)

    dashboard_pnl = get_dashboard_global_pnl()

    if isinstance(dashboard_pnl, dict):
        global_total_pnl = dashboard_pnl.get("active", 0.0)
        shadow_pnl = dashboard_pnl.get("shadow", 0.0)
        global_total_including_shadow = global_total_pnl + shadow_pnl
        global_realized_pnl = dashboard_pnl.get("realized_active", 0.0)
        global_unrealized_pnl = dashboard_pnl.get("unrealized_active", global_total_pnl - global_realized_pnl)
    else:
        shadow_pnl = options_realized + options_unrealized
        global_total_pnl = crypto_total
        global_total_including_shadow = crypto_total + shadow_pnl
        global_realized_pnl = crypto_realized
        global_unrealized_pnl = global_total_pnl - global_realized_pnl

    point = {
        "ts": utc_now_iso(),
        "total_pnl_eur": round(global_total_pnl, 2),
        "active_pnl_eur": round(global_total_pnl, 2),
        "shadow_pnl_eur": round(shadow_pnl, 2),
        "total_pnl_including_shadow_eur": round(global_total_including_shadow, 2),
        "realized_pnl_eur": round(global_realized_pnl, 2),
        "unrealized_pnl_eur": round(global_unrealized_pnl, 2),
        "capital_observed_eur": round(float(portfolio_state.get("capital_observed_eur", allocator_state.get("capital_observed_eur", 0.0)) or 0.0), 2),
        "capital_engaged_eur": round(float(portfolio_state.get("capital_engaged_eur", totals.get("live_exposure_sum_eur", 0.0)) or 0.0), 2),
        "live_exposure_ratio": round(float(portfolio_state.get("live_exposure_ratio", totals.get("live_exposure_sum", 0.0)) or 0.0), 4),
        "phase": str(
            allocator_state.get("phase")
            or portfolio_state.get("phase")
            or portfolio_state.get("portfolio_phase")
            or "UNKNOWN"
        ),
        "regime": str(
            allocator_state.get("regime")
            or portfolio_state.get("portfolio_regime")
            or "UNKNOWN"
        ),
    }

    history = existing.get("history", []) if isinstance(existing, dict) else []
    if not isinstance(history, list):
      history = []

    history.append(point)
    history = history[-MAX_POINTS:]

    return {
        "env": "PREPROD",
        "generated_at": utc_now_iso(),
        "history": history,
        "latest": point,
        "sources": {
            "pnl_state": str(PNL_STATE_PATH),
            "options_v2_daily_report": str(OPTIONS_V2_DAILY_REPORT_PATH),
            "capital_allocator_state": str(CAPITAL_ALLOCATOR_STATE_PATH),
            "portfolio_state": str(PORTFOLIO_STATE_PATH),
        },
    }


def save_equity_curve_state() -> dict:
    state = build_equity_curve_state()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    return state


if __name__ == "__main__":
    result = save_equity_curve_state()
    print(json.dumps(result, indent=2))
