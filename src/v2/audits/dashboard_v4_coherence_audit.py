from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
OUTPUT = DATA / "audits/dashboard_v4_coherence_audit.json"

DASHBOARD_V4 = ROOT / "src/v2/interface/react/src/pages/DashboardV4.jsx"
PORTFOLIO_TARGET = Path("/opt/nsc/data/preprod/portfolio/portfolio_target.json")
PORTFOLIO_STATE = Path("/opt/nsc/data/preprod/portfolio/state/portfolio_state.json")


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


txt = DASHBOARD_V4.read_text(encoding="utf-8") if DASHBOARD_V4.exists() else ""
target = read_json(PORTFOLIO_TARGET, {}) or {}
state = read_json(PORTFOLIO_STATE, {}) or {}

final_weights = target.get("final_brick_weights") or {}
bricks = state.get("bricks") or {}

failed = []

required_fetches = [
    "/dashboard/v3",
    "/api/portfolio_state",
    "/portfolio-target",
    "/dashboard/market_regime",
]

for endpoint in required_fetches:
    if endpoint not in txt:
        failed.append({
            "check": "dashboard_v4_fetches_endpoint",
            "severity": "critical",
            "detail": f"DashboardV4 does not fetch {endpoint}",
        })

for brick, weight in final_weights.items():
    state_weight = (bricks.get(brick) or {}).get("target_weight_snapshot")
    if state_weight is None:
        failed.append({
            "check": "state_contains_target_brick",
            "severity": "warning",
            "detail": f"{brick} missing from portfolio_state.bricks",
        })
        continue

    if abs(float(weight or 0) - float(state_weight or 0)) > 0.0001:
        failed.append({
            "check": "target_state_weight_match",
            "severity": "critical",
            "detail": f"{brick} target/state mismatch",
            "evidence": {
                "target": weight,
                "state": state_weight,
            },
        })

expected_active = {
    "crypto": 0.192857,
    "equities_offensive": 0.25,
    "equities_defensive": 0.20,
    "bonds": 0.15,
    "precious_metals": 0.08,
}

for brick, expected in expected_active.items():
    actual = final_weights.get(brick)
    if actual is None or abs(float(actual) - expected) > 0.0001:
        failed.append({
            "check": "master_weight_visible",
            "severity": "critical",
            "detail": f"{brick} target weight does not match Master.",
            "evidence": {
                "expected": expected,
                "actual": actual,
            },
        })

status = "ok"
if any(f["severity"] == "critical" for f in failed):
    status = "critical"
elif failed:
    status = "warning"

result = {
    "generated_at": utc_now(),
    "status": status,
    "engine": "dashboard_v4_coherence_audit_v1",
    "summary": {
        "dashboard_v4_exists": DASHBOARD_V4.exists(),
        "portfolio_target_regime": target.get("portfolio_regime"),
        "portfolio_state_regime": state.get("portfolio_regime"),
        "final_brick_weights": final_weights,
        "cash_buffer": target.get("cash_buffer"),
        "dashboard_fetches": {
            endpoint: endpoint in txt for endpoint in required_fetches
        },
    },
    "failed_checks": failed,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": status,
    "summary": result["summary"],
    "failed_checks": failed,
}, indent=2, ensure_ascii=False))
