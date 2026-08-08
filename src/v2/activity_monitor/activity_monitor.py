#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

from activity_registry import ENGINES

ROOT = Path("/opt/nsc/app")
PREPROD = Path("/opt/nsc/data/preprod")
OUT = ROOT / "data/preprod/activity"
OUT.mkdir(parents=True, exist_ok=True)

def read_json(path, default=None):
    try:
        p = Path(path)
        if not p.is_absolute():
            p = ROOT / path
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}

def read_jsonl(path, default=None):
    try:
        p = Path(path)
        if not p.is_absolute():
            p = ROOT / path
        if not p.exists():
            return default if default is not None else []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
        return out
    except Exception:
        return default if default is not None else []

def read_any(path, default=None):
    p = Path(path) if path else None
    if p and str(p).endswith(".jsonl"):
        return read_jsonl(p, default if default is not None else [])
    return read_json(path, default if default is not None else {})

def as_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ["orders", "fills", "positions", "data", "items", "rows"]:
            if isinstance(payload.get(k), list):
                return payload.get(k)
        if payload:
            return list(payload.values()) if all(isinstance(v, dict) for v in payload.values()) else []
    return []

def engine_execution_artifacts(eid):
    mapping = {
        "crypto": {
            "orders": PREPROD / "trading/execution_plan.json",
            "fills": PREPROD / "trading/fills.json",
            "positions": PREPROD / "trading/open_positions.json",
        },
        "equities_offensive": {
            "orders": PREPROD / "equities_offensive/execution/execution_plan.json",
            "fills": PREPROD / "equities_offensive/execution/fills.json",
            "positions": PREPROD / "equities_offensive/state/positions.json",
        },
        "equities_defensive": {
            "positions": ROOT / "data/defensive/state/exposure_snapshot.json",
            "fills": ROOT / "data/defensive/execution/simulated_fills.jsonl",
        },
        "long_term": {
            "positions": ROOT / "data/portfolio/long_term_positions.json",
        },
        "options_v2_shadow": {
            "positions": PREPROD / "options_v3/positions_open.json",
            "closed_positions": PREPROD / "options_v3/positions_closed.json",
        },
        "precious_metals": {
            "positions": ROOT / "data/metals/state/exposure_snapshot.json",
            "fills": ROOT / "data/metals/execution/simulated_fills.jsonl",
        },
        "bonds": {
            "positions": ROOT / "data/bonds/state/exposure_snapshot.json",
            "fills": ROOT / "data/bonds/execution/simulated_fills.jsonl",
        },
        "funding": {
            "orders": ROOT / "src/v2/data/portfolio/rebalance/funding_plan.json",
        },
        "treasury": {
            "orders": ROOT / "src/v2/data/portfolio/rebalance/rebalance_plan.json",
        },
    }
    return mapping.get(eid, {})

def now():
    return datetime.now(timezone.utc).isoformat()

def pct(x):
    try:
        return round(float(x) * 100, 2)
    except Exception:
        return 0.0

def score_from_freshness(is_fresh=True):
    return 95 if is_fresh else 60

def build_engine_snapshot(engine):
    eid = engine["id"]

    portfolio = read_json("src/v2/data/portfolio/state/portfolio_state.json", {})
    artifacts = engine_execution_artifacts(eid)
    execution_plan = read_json(artifacts.get("orders", "data/preprod/execution/execution_plan.json"), {})
    discovery = read_json("data/preprod/discovery/market_discovery_summary.json", {})
    meta_validation = read_json("data/preprod/discovery/meta_validation.json", {})
    risk = read_json("data/preprod/risk/risk_overview.json", {})

    bricks = portfolio.get("bricks") or portfolio.get("portfolio_bricks") or {}
    brick = bricks.get(eid, {}) if isinstance(bricks, dict) else {}

    orders = as_list(execution_plan)
    fills = as_list(read_any(artifacts.get("fills", ""), [])) if artifacts.get("fills") else []
    positions = as_list(read_any(artifacts.get("positions", ""), [])) if artifacts.get("positions") else []

    engine_orders = [
        o for o in orders
        if isinstance(o, dict) and (
            eid in str(o.get("strategy", "")).lower()
            or eid in str(o.get("brick", "")).lower()
            or eid in str(o.get("engine", "")).lower()
            or (eid == "crypto" and str(o.get("symbol", "")).lower().endswith("usdt"))
        )
    ]
    if eid in ["crypto", "equities_offensive"]:
        engine_orders = orders

    health = 95
    activity = 70
    alerts = []

    if engine.get("status") == "shadow":
        activity = 20

    if eid == "crypto":
        activity = 90 if orders else 75
        health = 96
    elif eid in ["equities_offensive", "equities_defensive", "bonds", "precious_metals"]:
        health = score_from_freshness(True)
        activity = 65
    elif eid == "discovery":
        tradable = discovery.get("tradable_opportunities", 0) or discovery.get("tradable_count", 0)
        activity = min(100, 60 + int(tradable or 0) * 10)
        health = 95
    elif eid == "execution":
        activity = 90 if orders else 60
        health = 96
    elif eid == "risk":
        health = 95
        activity = 80
    elif eid == "governance":
        drift = meta_validation.get("strategy_drift", False)
        health = 90 if drift else 98
        activity = 85
    elif eid == "treasury":
        health = 95
        activity = 75
    elif eid == "funding":
        health = 95
        activity = 70

    capital_pct = pct(brick.get("current", brick.get("current_weight", brick.get("current_weight_estimate", 0))))
    target_pct = pct(brick.get("target", brick.get("target_weight", brick.get("target_weight_snapshot", 0))))
    capital_gap_pct = round(capital_pct - target_pct, 2)

    if activity < 50 and engine.get("status") != "shadow":
        alerts.append({
            "severity": "warning",
            "type": "low_activity",
            "message": f"{engine['name']} activity is low",
        })

    if engine["group"] == "investment" and engine.get("status") != "shadow" and abs(capital_gap_pct) >= 10:
        alerts.append({
            "severity": "warning",
            "type": "capital_gap",
            "message": f"{engine['name']} capital allocation gap is {capital_gap_pct:+.2f} pts versus target",
            "capital_pct": capital_pct,
            "target_pct": target_pct,
            "gap_pct": capital_gap_pct,
        })

    return {
        "id": eid,
        "name": engine["name"],
        "group": engine["group"],
        "status": engine["status"],
        "health_score": health,
        "activity_score": activity,
        "capital_pct": capital_pct,
        "target_pct": target_pct,
        "capital_gap_pct": capital_gap_pct,
        "confidence_pct": pct(brick.get("confidence", 0)) if brick.get("confidence", 0) <= 1 else brick.get("confidence", 0),
        "orders_count": len(engine_orders),
        "fills_count": len(fills),
        "positions_count": len(positions),
        "last_event": "snapshot_generated",
        "alerts": alerts,
    }

def main():
    generated_at = now()
    engines = [build_engine_snapshot(e) for e in ENGINES]
    alerts = [a | {"engine": e["id"]} for e in engines for a in e["alerts"]]

    investment = [e for e in engines if e["group"] == "investment"]
    active_investment = [e for e in investment if e["status"] != "shadow"]

    avg_health = round(sum(e["health_score"] for e in engines) / max(1, len(engines)), 2)
    avg_activity = round(sum(e["activity_score"] for e in engines) / max(1, len(engines)), 2)
    gross_exposure = round(sum(e["capital_pct"] for e in investment), 2)
    capital_deployment = round(min(100.0, gross_exposure), 2)

    dashboard = {
        "generated_at": generated_at,
        "status": "healthy" if avg_health >= 90 and not alerts else "watch",
        "summary": {
            "portfolio_health": avg_health,
            "activity_score": avg_activity,
            "investment_engines_active": len(active_investment),
            "investment_engines_total": len(investment),
            "capital_deployment_pct": capital_deployment,
            "gross_exposure_pct": gross_exposure,
            "alerts_count": len(alerts),
        },
        "engines": engines,
        "alerts": alerts,
        "timeline": [
            {
                "timestamp": generated_at,
                "engine": "activity_monitor",
                "event_type": "snapshot",
                "message": "Portfolio Activity Monitor snapshot generated",
                "severity": "info",
            }
        ],
    }

    files = {
        "activity_dashboard.json": dashboard,
        "activity_scores.json": {"generated_at": generated_at, "engines": engines},
        "activity_alerts.json": {"generated_at": generated_at, "alerts": alerts},
        "activity_timeline.json": {"generated_at": generated_at, "events": dashboard["timeline"]},
        "activity_registry.json": {"generated_at": generated_at, "engines": ENGINES},
    }

    for name, payload in files.items():
        (OUT / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("===== NSC PORTFOLIO ACTIVITY MONITOR =====")
    print("Status:", dashboard["status"])
    print("Portfolio health:", avg_health)
    print("Activity score:", avg_activity)
    print("Capital deployment:", capital_deployment)
    print("Gross exposure:", gross_exposure)
    print("Alerts:", len(alerts))
    print("Output:", OUT)

if __name__ == "__main__":
    main()
