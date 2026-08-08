from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")

HISTORY_SUMMARY_PATH = DATA_DIR / "discovery" / "meta_validation_history_summary.json"
OUT_PATH = DATA_DIR / "discovery" / "meta_health_monitor.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    hist = load_json(HISTORY_SUMMARY_PATH, default={}) or {}

    history_count = int(hist.get("history_count") or 0)
    avg_alignment = float(hist.get("avg_decision_alignment") or 0.0)
    avg_coverage = float(hist.get("avg_opportunity_coverage") or 0.0)
    drift_count = int(hist.get("drift_count") or 0)
    healthy_ratio = float(hist.get("healthy_ratio") or 0.0)

    latest = hist.get("latest", {}) if isinstance(hist.get("latest"), dict) else {}
    latest_health = latest.get("pipeline_health")
    latest_drift = latest.get("strategy_drift")
    latest_alignment = float(latest.get("decision_alignment_score") or 0.0)

    alerts = []
    status = "healthy"

    if latest_drift is True:
        alerts.append("latest_strategy_drift")
        status = "drift_alert"

    if avg_alignment < 70:
        alerts.append("avg_alignment_below_70")
        status = "warning" if status != "drift_alert" else status

    if latest_alignment < 70:
        alerts.append("latest_alignment_below_70")
        status = "warning" if status != "drift_alert" else status

    if drift_count >= 2:
        alerts.append("multiple_drifts_detected")
        status = "drift_alert"

    if healthy_ratio < 80 and history_count >= 5:
        alerts.append("healthy_ratio_below_80")
        status = "warning" if status != "drift_alert" else status

    if avg_coverage < 20 and history_count >= 5:
        alerts.append("low_opportunity_coverage_trend")
        if status == "healthy":
            status = "watch"

    if history_count < 5 and status == "healthy":
        status = "warming_up"
        alerts.append("insufficient_history")

    if status in {"healthy", "warming_up"}:
        severity = "info"
    elif status == "watch":
        severity = "watch"
    elif status == "warning":
        severity = "warning"
    else:
        severity = "critical"

    payload = {
        "status": status,
        "severity": severity,
        "generated_at": utc_now(),
        "engine": "meta_health_monitor_v1",
        "history_count": history_count,
        "avg_decision_alignment": avg_alignment,
        "avg_opportunity_coverage": avg_coverage,
        "drift_count": drift_count,
        "healthy_ratio": healthy_ratio,
        "latest": {
            "pipeline_health": latest_health,
            "strategy_drift": latest_drift,
            "decision_alignment_score": latest_alignment,
            "execution_symbols": latest.get("execution_symbols", []),
        },
        "alerts": alerts,
        "summary": (
            f"status={status} | avg_alignment={avg_alignment:.2f}% | "
            f"avg_coverage={avg_coverage:.2f}% | drift_count={drift_count} | "
            f"healthy_ratio={healthy_ratio:.2f}%"
        ),
    }

    save_json(OUT_PATH, payload)

    print({
        "output": str(OUT_PATH),
        "engine": payload["engine"],
        "status": payload["status"],
        "severity": payload["severity"],
        "alerts": payload["alerts"],
    })


if __name__ == "__main__":
    main()
