from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod")
ANALYSIS = BASE / "analysis"
REPORTS = BASE / "reports"

SOURCES = {
    BASE / "average_sentiment.json": ANALYSIS / "average_sentiment.json",
    BASE / "sentiment_overview.json": ANALYSIS / "sentiment_overview.json",
    REPORTS / "average_sentiment.json": ANALYSIS / "average_sentiment_reports_copy.json",
}

OUT = ANALYSIS / "preprod_analysis_bridge_status.json"


def copy_if_exists(src: Path, dst: Path):
    if not src.exists():
        return {"source": str(src), "target": str(dst), "status": "missing"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {
        "source": str(src),
        "target": str(dst),
        "status": "copied",
        "source_mtime": src.stat().st_mtime,
        "size": src.stat().st_size,
    }


def main():
    ANALYSIS.mkdir(parents=True, exist_ok=True)

    results = [copy_if_exists(src, dst) for src, dst in SOURCES.items()]

    payload = {
        "status": "ok",
        "engine": "preprod_analysis_bridge_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
