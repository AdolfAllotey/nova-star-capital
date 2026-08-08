from pathlib import Path
import json
from datetime import datetime, timezone

DATA = Path("/opt/nsc/data/preprod/documentation")
INDEX = DATA / "masterbook_index.json"
COVERAGE = DATA / "coverage_report.json"
OUT = DATA / "documentation_health.json"


def build_health():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    cov = json.loads(COVERAGE.read_text(encoding="utf-8"))

    docs = idx.get("documents", [])
    total = len(docs)

    missing_classification = sum(1 for d in docs if d.get("classification") in ("", "unknown"))
    missing_status = sum(1 for d in docs if d.get("status") in ("", "unknown"))
    too_short = sum(1 for d in docs if int(d.get("word_count") or 0) < 80)

    penalties = (
        missing_classification * 0.25
        + missing_status * 0.15
        + too_short * 0.25
        + max(0, 100 - cov.get("coverage_score", 0)) * 0.25
    )

    health = max(0, round(100 - penalties, 2))

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "documentation_health": health,
        "documents_count": total,
        "coverage_score": cov.get("coverage_score"),
        "missing_classification": missing_classification,
        "missing_status": missing_status,
        "too_short_documents": too_short,
        "status": "healthy" if health >= 90 else "watch" if health >= 75 else "degraded",
    }

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


if __name__ == "__main__":
    payload = build_health()
    print("Documentation health:", payload["documentation_health"])
    print(OUT)
