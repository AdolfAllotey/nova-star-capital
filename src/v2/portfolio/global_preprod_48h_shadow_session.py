from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod/portfolio/audit")
OUT = BASE / "global_preprod_48h_shadow_session.json"

now = datetime.now(timezone.utc).isoformat()

payload = {
    "status": "active",
    "engine": "global_preprod_48h_shadow_session_v1",
    "started_at": now,
    "target_duration_hours": 48,
    "mode": "SHADOW_PREPROD",
    "execution_policy": "SIMULATED_ONLY",
    "objectives": [
        "validate continuous global PREPROD cycle stability",
        "monitor failed runs, trend drift, anomaly state and readiness status",
        "prepare GO/NO-GO evidence for longer PREPROD"
    ],
    "success_criteria": {
        "failed_runs": 0,
        "trend_status": "HEALTHY",
        "anomaly_status": "CLEAR",
        "readiness_status": "READY",
        "stress_failed": 0
    }
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
