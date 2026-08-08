from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod")
OUT = BASE / "portfolio/audit/global_dynamic_metrics_audit.json"

CHECKS = [
    {
        "name": "dashboard_confidence",
        "path": BASE / "portfolio/portfolio_target.json",
        "field": "brick_confidence",
    },
    {
        "name": "governance_mode",
        "path": BASE / "analysis/governance_engine_pro.json",
        "field": "action_policy",
    },
    {
        "name": "execution_plan",
        "path": BASE / "trading/execution_plan.json",
        "field": "orders",
    },
    {
        "name": "portfolio_state",
        "path": BASE / "portfolio/state/portfolio_state.json",
        "field": "bricks",
    },
    {
        "name": "signal_votes",
        "path": BASE / "analysis/signal_votes.json",
        "field": None,
    },
]

def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

results = []

for check in CHECKS:
    path = check["path"]
    data = load_json(path)

    exists = path.exists()
    valid_json = data is not None

    stale = False
    freshness_sec = None

    if exists:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        freshness_sec = round(
            (datetime.now(timezone.utc) - mtime).total_seconds(),
            2
        )
        stale = freshness_sec > 3600

    field_exists = False

    if check.get("field") is None:
        field_exists = isinstance(data, (dict, list))
    elif isinstance(data, dict):
        field_exists = check["field"] in data

    results.append({
        "metric": check["name"],
        "file": str(path),
        "exists": exists,
        "valid_json": valid_json,
        "field_exists": field_exists,
        "freshness_sec": freshness_sec,
        "stale": stale,
        "status":
            "OK"
            if exists and valid_json and field_exists and not stale
            else "WARNING"
    })

global_status = (
    "OK"
    if all(r["status"] == "OK" for r in results)
    else "WARNING"
)

payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "global_status": global_status,
    "metrics_checked": len(results),
    "ok_metrics": len([r for r in results if r["status"] == "OK"]),
    "warning_metrics": len([r for r in results if r["status"] != "OK"]),
    "results": results,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2))

print(f"[OK] dynamic metrics audit -> {OUT}")
