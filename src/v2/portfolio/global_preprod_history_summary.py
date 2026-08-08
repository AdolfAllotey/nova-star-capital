from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_DIR = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_cycle_history")
OUT = Path("/opt/nsc/data/preprod/portfolio/audit/global_preprod_history_summary.json")

runs = []

for p in sorted(HISTORY_DIR.glob("global_preprod_cycle_*.json")):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        stress = d.get("stress_tests") or {}
        stress_summary = stress.get("summary") or {}

        runs.append({
            "file": p.name,
            "status": d.get("status"),
            "started_at": d.get("started_at"),
            "finished_at": d.get("finished_at"),
            "pipeline_rc": d.get("pipeline_rc"),
            "kernel_rc": d.get("kernel_rc"),
            "institutional_layer_ready": d.get("institutional_layer_ready"),
            "global_status": d.get("global_status"),
            "gate_mode": (d.get("gate") or {}).get("mode"),
            "stress_status": stress.get("status"),
            "stress_failed": stress_summary.get("failed"),
        })
    except Exception as e:
        runs.append({
            "file": p.name,
            "status": "unreadable",
            "error": str(e),
        })

def is_success(r: dict) -> bool:
    return (
        r.get("status") == "ok"
        and r.get("pipeline_rc") == 0
        and r.get("kernel_rc") == 0
        and r.get("institutional_layer_ready") is True
        and r.get("global_status") == "OK"
    )

def is_failed(r: dict) -> bool:
    return not is_success(r)

successful = [r for r in runs if is_success(r)]
failed = [r for r in runs if is_failed(r)]
degraded = [
    r for r in successful
    if (r.get("stress_failed") or 0) > 0
    or str(r.get("stress_status") or "").lower() == "warning"
]

payload = {
    "status": "ok" if not failed else "warning",
    "engine": "global_preprod_history_summary_v1_1_failed_vs_degraded",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "summary": {
        "total_runs": len(runs),
        "successful_runs": len(successful),
        "failed_runs": len(failed),
        "degraded_runs": len(degraded),
    },
    "last_run": runs[-1] if runs else None,
    "failed_runs": failed[-10:],
    "degraded_runs": degraded[-10:],
    "notes": [
        "failed_runs counts only technical/blocking failed cycles.",
        "degraded_runs counts successful cycles with residual stress warnings."
    ],
}

OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
