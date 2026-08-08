#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Provider Validation Runner V1

Enchaîne :
1. validation cross-source générique ;
2. quality gate strict ou observation.

Aucune promotion canonique.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CODE_DIR = Path(__file__).resolve().parent

VALIDATOR = (
    CODE_DIR
    / "provider_cross_source_validator_v1.py"
)

GATE = (
    CODE_DIR
    / "provider_quality_gate_v1.py"
)

DATA_DIR = Path(
    "/opt/nsc/data/preprod/equities_offensive/"
    "market/providers"
)

DEFAULT_PRIMARY = (
    DATA_DIR / "market_data_yfinance_v1.json"
)

DEFAULT_SECONDARY = (
    DATA_DIR / "market_data_massive_v1.json"
)

DEFAULT_VALIDATION = (
    DATA_DIR / "cross_source_validation_v1.json"
)

DEFAULT_GATE = (
    DATA_DIR / "provider_quality_gate_v1.json"
)

DEFAULT_RUN_REPORT = (
    DATA_DIR / "provider_validation_run_v1.json"
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
        "command": command,
        "return_code": completed.returncode,
        "successful": (
            completed.returncode
            in accepted_codes
        ),
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--primary",
        type=Path,
        default=DEFAULT_PRIMARY,
    )

    parser.add_argument(
        "--secondary",
        type=Path,
        default=DEFAULT_SECONDARY,
    )

    parser.add_argument(
        "--validation-output",
        type=Path,
        default=DEFAULT_VALIDATION,
    )

    parser.add_argument(
        "--gate-output",
        type=Path,
        default=DEFAULT_GATE,
    )

    parser.add_argument(
        "--run-report",
        type=Path,
        default=DEFAULT_RUN_REPORT,
    )

    parser.add_argument(
        "--observation-mode",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    started_at = utc_now_iso()
    steps: list[dict[str, Any]] = []

    validation_command = [
        sys.executable,
        str(VALIDATOR),
        "--primary",
        str(args.primary),
        "--secondary",
        str(args.secondary),
        "--output",
        str(args.validation_output),
    ]

    validation_step = run_step(
        "cross_source_validation",
        validation_command,
        {0},
    )

    steps.append(validation_step)

    if not validation_step["successful"]:
        write_json(
            args.run_report,
            {
                "schema_version": "1.0",
                "generated_at": utc_now_iso(),
                "started_at": started_at,
                "status": (
                    "blocked_at_validation"
                ),
                "canonical_files_modified": False,
                "promotion_executed": False,
                "steps": steps,
            },
        )

        return 10

    gate_command = [
        sys.executable,
        str(GATE),
        "--validation",
        str(args.validation_output),
        "--output",
        str(args.gate_output),
    ]

    if args.observation_mode:
        gate_command.append(
            "--observation-mode"
        )

    gate_step = run_step(
        "provider_quality_gate",
        gate_command,
        {0, 1, 2},
    )

    steps.append(gate_step)

    gate_payload: dict[str, Any] = {}

    if args.gate_output.exists():
        gate_payload = json.loads(
            args.gate_output.read_text(
                encoding="utf-8"
            )
        )

    decision = gate_payload.get(
        "decision",
        "UNKNOWN",
    )

    status = {
        "PASS": "quality_gate_passed",
        "WARNING": "quality_gate_warning",
        "FAIL": "quality_gate_failed",
    }.get(
        decision,
        "quality_gate_unknown",
    )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_provider_"
            "validation_run"
        ),
        "generated_at": utc_now_iso(),
        "started_at": started_at,
        "status": status,
        "quality_gate_decision": decision,
        "observation_mode": (
            args.observation_mode
        ),
        "canonical_files_modified": False,
        "promotion_executed": False,
        "artifacts": {
            "primary": str(args.primary),
            "secondary": str(args.secondary),
            "validation": str(
                args.validation_output
            ),
            "quality_gate": str(
                args.gate_output
            ),
        },
        "steps": steps,
    }

    write_json(
        args.run_report,
        report,
    )

    print(
        json.dumps(
            {
                "status": status,
                "quality_gate_decision": decision,
                "observation_mode": (
                    args.observation_mode
                ),
                "run_report": str(
                    args.run_report
                ),
                "canonical_files_modified": False,
                "promotion_executed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return {
        "PASS": 0,
        "WARNING": 1,
        "FAIL": 2,
    }.get(decision, 3)


if __name__ == "__main__":
    sys.exit(main())
