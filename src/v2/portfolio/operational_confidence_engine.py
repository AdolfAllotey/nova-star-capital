from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path("/opt/nsc/data/preprod")
OUT = BASE / "portfolio/audit/operational_confidence.json"

SOURCES = {
    "global_audit": BASE / "portfolio/audit/global_orchestration_audit.json",
    "supervision": BASE / "portfolio/audit/institutional_supervision_summary.json",
    "trend": BASE / "portfolio/audit/global_preprod_trend_monitor.json",
    "anomaly": BASE / "portfolio/audit/global_preprod_anomaly_detector.json",
    "readiness": BASE / "portfolio/audit/global_preprod_long_run_readiness.json",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> dict:
    global_audit = load(SOURCES["global_audit"], {})
    supervision = load(SOURCES["supervision"], {})
    trend = load(SOURCES["trend"], {})
    anomaly = load(SOURCES["anomaly"], {})
    readiness = load(SOURCES["readiness"], {})

    checks = []

    checks.append(("global_audit_ok", global_audit.get("global_status") == "OK", 0.25))
    checks.append(("supervision_ok", supervision.get("global_status") == "OK", 0.20))
    checks.append(("trend_healthy", trend.get("trend_status") == "HEALTHY", 0.20))
    checks.append(("anomaly_clear", anomaly.get("anomaly_status") == "CLEAR", 0.20))
    checks.append(("readiness_ready", readiness.get("readiness_status") == "READY", 0.15))

    score = sum(weight for _, passed, weight in checks if passed)
    total = sum(weight for _, _, weight in checks)
    confidence = round(score / total, 4) if total else 0.0

    result = {
        "status": "ok",
        "engine": "operational_confidence_engine_v1",
        "generated_at": now(),
        "confidence": confidence,
        "confidencePct": round(confidence * 100, 2),
        "label": "Operational",
        "checks": [
            {"name": name, "passed": passed, "weight": weight}
            for name, passed, weight in checks
        ],
        "sources": {k: str(v) for k, v in SOURCES.items()},
    }

    save(OUT, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
