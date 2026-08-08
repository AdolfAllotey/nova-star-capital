#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Promotion Readiness Runner V1

Enchaîne :
1. provenance ;
2. promotion dry-run ;
3. funnel.

Aucune promotion réelle.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CODE_DIR = Path(__file__).resolve().parent

PROVENANCE = (
    CODE_DIR / "provider_provenance_report_v1.py"
)

PROMOTION = (
    CODE_DIR / "provider_promotion_manager_v1.py"
)

FUNNEL = (
    CODE_DIR / "provider_decision_funnel_v1.py"
)

DATA_DIR = Path(
    "/opt/nsc/data/preprod/equities_offensive/"
    "market/providers"
)

RUN_REPORT = (
    DATA_DIR / "promotion_readiness_run_v1.json"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def run_step(
    name: str,
    command: list[str],
    accepted_codes: set[int],
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.stdout:
        print(completed.stdout, end="")

    if completed.stderr:
        print(
            completed.stderr,
            file=sys.stderr,
            end="",
        )

    return {
        "name": name,
        "return_code": completed.returncode,
        "successful": (
            completed.returncode in accepted_codes
        ),
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def main() -> int:
    started_at = utc_now_iso()
    steps: list[dict[str, Any]] = []

    steps.append(
        run_step(
            "provenance",
            [
                sys.executable,
                str(PROVENANCE),
            ],
            {0},
        )
    )

    steps.append(
        run_step(
            "promotion_dry_run",
            [
                sys.executable,
                str(PROMOTION),
            ],
            {0, 1},
        )
    )

    steps.append(
        run_step(
            "decision_funnel",
            [
                sys.executable,
                str(FUNNEL),
            ],
            {0},
        )
    )

    successful = all(
        step["successful"]
        for step in steps
    )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_promotion_readiness_run"
        ),
        "generated_at": utc_now_iso(),
        "started_at": started_at,
        "status": (
            "completed"
            if successful
            else "completed_with_errors"
        ),
        "canonical_files_modified": False,
        "promotion_executed": False,
        "steps": steps,
    }

    RUN_REPORT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": report["status"],
                "run_report": str(RUN_REPORT),
                "canonical_files_modified": False,
                "promotion_executed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if successful else 1


if __name__ == "__main__":
    sys.exit(main())
