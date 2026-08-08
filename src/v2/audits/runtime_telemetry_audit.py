from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"

HISTORY_DIR = DATA / "audits/history/preprod_daily_health"
OUTPUT = DATA / "audits/runtime_telemetry_audit.json"
DYNAMIC_SIGNAL_ACTIVITY = DATA / "audits/dynamic_signal_activity_audit.json"

MIN_POINTS_FOR_FREEZE = 3


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def stable(values):
    cleaned = [v for v in values if v is not None]
    if len(cleaned) < MIN_POINTS_FOR_FREEZE:
        return False
    return len(set(json.dumps(v, sort_keys=True) for v in cleaned)) == 1


snapshots = []

for path in sorted(HISTORY_DIR.glob("preprod_daily_health_report_*.json"))[-20:]:
    doc = read_json(path, {}) or {}
    if doc:
        snapshots.append({
            "path": str(path),
            "timestamp": doc.get("timestamp"),
            "doc": doc,
        })


failed = []
stable_expected = []
dynamic_signal_activity = read_json(DYNAMIC_SIGNAL_ACTIVITY, {}) or {}
dynamic_status = dynamic_signal_activity.get("status")

series = {
    "count": len(snapshots),
    "timestamps": [s.get("timestamp") for s in snapshots],
}

brick_confidence_series = defaultdict(list)
brick_regime_series = defaultdict(list)
brick_target_series = defaultdict(list)
portfolio_regime_series = []
cash_buffer_series = []
decision_series = []
status_series = []

for s in snapshots:
    doc = s["doc"]

    status_series.append(doc.get("status"))
    decision_series.append((doc.get("daily_decision") or {}).get("decision"))

    portfolio = doc.get("portfolio_health") or {}
    portfolio_regime_series.append(portfolio.get("portfolio_regime"))
    cash_buffer_series.append(portfolio.get("cash_buffer"))

    bricks = doc.get("bricks_health") or {}
    for name, brick in bricks.items():
        if not isinstance(brick, dict):
            continue

        brick_confidence_series[name].append(brick.get("confidence"))
        brick_regime_series[name].append(brick.get("regime"))
        brick_target_series[name].append(brick.get("target_weight_snapshot"))


# =========================================================
# Freeze detection
# =========================================================

freeze_report = {
    "portfolio_regime_frozen": stable(portfolio_regime_series),
    "cash_buffer_frozen": stable(cash_buffer_series),
    "brick_confidence_frozen": {},
    "brick_regime_frozen": {},
    "brick_target_frozen": {},
}

for name, values in brick_confidence_series.items():
    freeze_report["brick_confidence_frozen"][name] = {
        "frozen": stable(values),
        "values": values[-10:],
    }

for name, values in brick_regime_series.items():
    freeze_report["brick_regime_frozen"][name] = {
        "frozen": stable(values),
        "values": values[-10:],
    }

for name, values in brick_target_series.items():
    freeze_report["brick_target_frozen"][name] = {
        "frozen": stable(values),
        "values": values[-10:],
    }


if len(snapshots) < MIN_POINTS_FOR_FREEZE:
    failed.append({
        "check": "enough_history_points",
        "severity": "warning",
        "detail": "Not enough health report history points for freeze detection.",
        "evidence": {
            "snapshots": len(snapshots),
            "required": MIN_POINTS_FOR_FREEZE,
        },
    })


# Portfolio regime frozen can be expected when the signal activity audit is healthy.
if freeze_report["portfolio_regime_frozen"]:
    item = {
        "check": "portfolio_regime_frozen",
        "severity": "info" if dynamic_status == "ok" else "warning",
        "detail": "Portfolio regime has not changed across recent health snapshots.",
        "evidence": portfolio_regime_series[-10:],
    }
    if dynamic_status == "ok":
        stable_expected.append(item)
    else:
        failed.append(item)


# Confidence frozen is a stronger signal because it often reveals static inputs.
frozen_confidences = {
    name: data
    for name, data in freeze_report["brick_confidence_frozen"].items()
    if data.get("frozen")
}

if frozen_confidences:
    item = {
        "check": "brick_confidence_frozen",
        "severity": "info" if dynamic_status == "ok" else "warning",
        "detail": "One or more brick confidence values are frozen across recent health snapshots.",
        "evidence": frozen_confidences,
    }
    if dynamic_status == "ok":
        stable_expected.append(item)
    else:
        failed.append(item)


# Target weights may be intentionally stable, so this is informational only.
frozen_targets = {
    name: data
    for name, data in freeze_report["brick_target_frozen"].items()
    if data.get("frozen")
}


def status_from_failed(items):
    if any(x.get("severity") == "critical" for x in items):
        return "critical"
    if items:
        return "warning"
    return "ok"


result = {
    "generated_at": utc_now(),
    "status": status_from_failed(failed),
    "engine": "runtime_telemetry_audit_v1",
    "summary": {
        "snapshots_analyzed": len(snapshots),
        "first_snapshot": snapshots[0]["timestamp"] if snapshots else None,
        "last_snapshot": snapshots[-1]["timestamp"] if snapshots else None,
        "latest_status": status_series[-1] if status_series else None,
        "latest_decision": decision_series[-1] if decision_series else None,
        "portfolio_regime_series": portfolio_regime_series[-10:],
        "cash_buffer_series": cash_buffer_series[-10:],
        "frozen_confidence_count": len(frozen_confidences),
        "frozen_target_count": len(frozen_targets),
    },
    "freeze_report": freeze_report,
    "informational": {
        "frozen_targets": frozen_targets,
        "stable_expected": stable_expected,
        "dynamic_signal_activity_status": dynamic_status,
        "note": "Stable regime/confidence is informational when dynamic signal activity is healthy.",
    },
    "failed_checks": failed,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": result["status"],
    "summary": result["summary"],
    "failed_checks": failed,
}, indent=2, ensure_ascii=False))
