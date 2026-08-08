from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/nsc/app")
DATA = ROOT / "data"
OUTPUT = DATA / "audits/fake_refresh_diagnostic.json"

DYNAMIC_AUDIT = DATA / "audits/dynamic_signal_activity_audit.json"
HISTORY_DIR = DATA / "audits/history/dynamic_signal_activity"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path, default=None):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


audit = read_json(DYNAMIC_AUDIT, {}) or {}
activity = audit.get("activity") or {}
artifacts = audit.get("artifacts") or {}

fake_refresh_artifacts = [
    name for name, data in activity.items()
    if isinstance(data, dict) and data.get("status") == "fake_refresh_possible"
]

snapshots = []
for path in sorted(HISTORY_DIR.glob("dynamic_signal_activity_*.json"))[-5:]:
    doc = read_json(path, {}) or {}
    if doc:
        snapshots.append({
            "path": str(path),
            "generated_at": doc.get("generated_at"),
            "artifacts": doc.get("artifacts") or {},
        })

diagnostics = {}

for name in fake_refresh_artifacts:
    timeline = []

    for snap in snapshots:
        a = (snap.get("artifacts") or {}).get(name) or {}
        timeline.append({
            "snapshot": snap.get("generated_at"),
            "sha256": a.get("sha256"),
            "age_seconds": a.get("age_seconds"),
            "signals": a.get("signals"),
        })

    current = artifacts.get(name) or {}

    diagnostics[name] = {
        "path": current.get("path"),
        "current_age_seconds": current.get("age_seconds"),
        "current_signals": current.get("signals"),
        "timeline": timeline,
        "likely_interpretation": (
            "file_rewritten_but_business_fields_static"
            if len(timeline) >= 2
            else "insufficient_history"
        ),
        "recommended_next_check": [
            "inspect_writer_module",
            "verify_if_timestamp_or_metadata_changes_only",
            "verify_if_signal_extraction_fields_are_complete",
            "check_scheduler_frequency",
        ],
    }


result = {
    "generated_at": utc_now(),
    "status": "warning" if fake_refresh_artifacts else "ok",
    "engine": "fake_refresh_diagnostic_v1",
    "summary": {
        "fake_refresh_count": len(fake_refresh_artifacts),
        "fake_refresh_artifacts": fake_refresh_artifacts,
        "snapshots_used": len(snapshots),
    },
    "diagnostics": diagnostics,
    "notes": [
        "This diagnostic explains fake_refresh_possible warnings from dynamic_signal_activity_audit.",
        "A fake refresh means file hash changed while extracted business signal fields stayed identical.",
    ],
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({
    "status": result["status"],
    "summary": result["summary"],
    "diagnostics": diagnostics,
}, indent=2, ensure_ascii=False))
