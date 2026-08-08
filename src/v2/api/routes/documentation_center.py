from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter(prefix="/api/documentation-center", tags=["documentation-center"])

DATA = Path("/opt/nsc/data/preprod/documentation")
MASTER = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")


def load_json(name, default):
    path = DATA / name
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


@router.get("")
def documentation_center():
    health = load_json("documentation_health.json", {})
    coverage = load_json("coverage_report.json", {})
    index = load_json("masterbook_index.json", {})

    return {
        "status": health.get("status", "unknown"),
        "documentation_health": health.get("documentation_health", 0),
        "coverage_score": health.get("coverage_score", coverage.get("coverage_score", 0)),
        "documents_count": health.get("documents_count", index.get("documents_count", 0)),
        "missing_classification": health.get("missing_classification", 0),
        "missing_status": health.get("missing_status", 0),
        "too_short_documents": health.get("too_short_documents", 0),
        "generated_utc": health.get("generated_utc"),
    }


@router.get("/coverage")
def documentation_coverage():
    return load_json("coverage_report.json", {})


@router.get("/index")
def documentation_index():
    return load_json("masterbook_index.json", {"documents_count": 0, "documents": []})


@router.get("/quality")
def documentation_quality():
    path = MASTER / "DOCUMENTATION_QUALITY_ISSUES.md"
    return {
        "path": str(path),
        "content": path.read_text(encoding="utf-8") if path.exists() else "",
    }


@router.get("/report")
def documentation_report():
    path = MASTER / "DOCUMENTATION_CENTER_REPORT.md"
    return {
        "path": str(path),
        "content": path.read_text(encoding="utf-8") if path.exists() else "",
    }
