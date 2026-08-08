from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from fastapi import APIRouter

router = APIRouter(tags=["system-status"])

DATA_ROOT = Path("/opt/nsc/data/preprod")

ARTEFACTS = {
    "system_metrics": DATA_ROOT / "telemetry" / "system_metrics_pro.json",
    "governance": DATA_ROOT / "analysis" / "governance_engine_pro.json",
    "orchestrator": DATA_ROOT / "telemetry" / "orchestrator_pro.json",
    "portfolio_state": DATA_ROOT / "portfolio" / "state" / "portfolio_state.json",
    "dashboard_v3_source": DATA_ROOT / "portfolio" / "state" / "portfolio_state.json",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def artefact_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "available": False,
            "path": str(path),
            "age_seconds": None,
            "modified_at": None,
            "json_valid": False,
        }

    modified = datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=timezone.utc,
    )

    age_seconds = max(
        0.0,
        (utc_now() - modified).total_seconds(),
    )

    payload = read_json(path)

    return {
        "available": True,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "modified_at": iso_utc(modified),
        "age_seconds": round(age_seconds, 3),
        "json_valid": payload is not None,
    }


@router.get("/api/status")
def system_status() -> dict[str, Any]:
    artefacts = {
        name: artefact_status(path)
        for name, path in ARTEFACTS.items()
    }

    missing = [
        name
        for name, info in artefacts.items()
        if not info["available"]
    ]

    invalid = [
        name
        for name, info in artefacts.items()
        if info["available"] and not info["json_valid"]
    ]

    critical = {
        "governance",
        "portfolio_state",
    }

    critical_missing = sorted(
        critical.intersection(set(missing + invalid))
    )

    degraded = bool(missing or invalid)

    return {
        "status": "degraded" if degraded else "ok",
        "engine": "nsc_system_status_v1",
        "env": "PREPROD",
        "generated_at": iso_utc(utc_now()),
        "degraded": degraded,
        "critical_failure": bool(critical_missing),
        "critical_missing": critical_missing,
        "missing": sorted(missing),
        "invalid": sorted(invalid),
        "artefacts": artefacts,
        "summary": {
            "artefacts_total": len(artefacts),
            "artefacts_available": sum(
                1
                for info in artefacts.values()
                if info["available"]
            ),
            "artefacts_missing": len(missing),
            "artefacts_invalid": len(invalid),
        },
    }
