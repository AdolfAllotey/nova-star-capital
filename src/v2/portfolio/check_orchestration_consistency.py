from __future__ import annotations

import json
import subprocess
from pathlib import Path

ARTIFACT = Path("/opt/nsc/data/preprod/portfolio/audit/orchestration_status.json")
CONTROL_ROOM = Path("/opt/nsc/app/src/v2/interface/react/src/pages/ControlRoom.jsx")
OUT = Path("/opt/nsc/data/preprod/portfolio/audit/orchestration_consistency.json")

status = "ok"
reasons = []

# --- artifact ---
try:
    artifact = json.loads(ARTIFACT.read_text())
except Exception as e:
    artifact = {}
    status = "error"
    reasons.append(f"artifact_unreadable:{e}")

artifact_status = artifact.get("orchestration_status")

# --- dashboard api ---
dashboard_status = None

try:
    raw = subprocess.check_output(
        [
            "bash",
            "-lc",
            "curl -sS http://127.0.0.1:8000/dashboard/v3"
        ],
        text=True,
        timeout=5,
    )

    d = json.loads(raw)
    dashboard_status = d.get("global", {}).get("orchestrationStatus")

except Exception as e:
    status = "error"
    reasons.append(f"dashboard_unreachable:{e}")

# --- ui source ---
ui_has_badge = False

try:
    txt = CONTROL_ROOM.read_text(encoding="utf-8")
    ui_has_badge = "ORCH {orchestrationStatus}" in txt
except Exception as e:
    status = "error"
    reasons.append(f"ui_unreadable:{e}")

# --- consistency ---
if artifact_status != dashboard_status:
    status = "error"
    reasons.append("artifact_dashboard_mismatch")

if not ui_has_badge:
    status = "error"
    reasons.append("ui_badge_missing")

blocking = status != "ok"

payload = {
    "status": status,
    "blocking": blocking,
    "alert_level": "BLOCKING" if blocking else "OK",
    "artifact_status": artifact_status,
    "dashboard_status": dashboard_status,
    "ui_has_badge": ui_has_badge,
    "reasons": reasons or ["all_checks_ok"],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

print(json.dumps(payload, indent=2))
