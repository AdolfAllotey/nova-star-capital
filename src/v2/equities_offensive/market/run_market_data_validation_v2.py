#!/usr/bin/env python3
"""
Nova Star Capital
Runner isolé — Offensive Equities Market Data Validation V2

Enchaîne :
1. collecte Stooq ;
2. validation YFinance / Stooq ;
3. Data Quality Gate.

Ce runner :
- ne modifie pas le pipeline actif ;
- ne modifie aucun fichier canonique ;
- ne réalise aucune promotion.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("nsc.run_market_data_validation_v2")

MODULE_DIRECTORY = Path(__file__).resolve().parent

STOOQ_SCRIPT = MODULE_DIRECTORY / "stooq_market_data_refresher.py"
VALIDATOR_SCRIPT = MODULE_DIRECTORY / "cross_source_validator.py"
GATE_SCRIPT = MODULE_DIRECTORY / "data_quality_gate.py"

DEFAULT_STOOQ_OUTPUT = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/market_data_stooq_v1.json"
)
DEFAULT_VALIDATION_OUTPUT = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/"
    "cross_source_validation_v1.json"
)
DEFAULT_GATE_OUTPUT = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/"
    "market_data_quality_gate_v1.json"
)
DEFAULT_RUN_REPORT = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/"
    "market_data_validation_run_v2.json"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_step(
    name: str,
    command: list[str],
    accepted_return_codes: set[int],
) -> dict[str, Any]:
    LOGGER.info("Démarrage étape %s", name)
    LOGGER.debug("Commande : %s", " ".join(command))

    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    successful = completed.returncode in accepted_return_codes

    if successful:
        LOGGER.info(
            "Étape %s terminée avec code %s",
            name,
            completed.returncode,
        )
    else:
        LOGGER.error(
            "Étape %s échouée avec code %s",
            name,
            completed.returncode,
        )

    if completed.stdout:
        print(completed.stdout, end="")

    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")

    return {
        "name": name,
        "command": command,
        "return_code": completed.returncode,
        "successful": successful,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Runner isolé Market Data Validation V2."
    )
    parser.add_argument(
        "--yfinance",
        type=Path,
        help="Chemin exact facultatif de l'artefact YFinance V2.",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        help="Liste facultative des symboles à comparer.",
    )
    parser.add_argument(
        "--symbols-file",
        type=Path,
    )
    parser.add_argument(
        "--stooq-output",
        type=Path,
        default=DEFAULT_STOOQ_OUTPUT,
    )
    parser.add_argument(
        "--validation-output",
        type=Path,
        default=DEFAULT_VALIDATION_OUTPUT,
    )
    parser.add_argument(
        "--gate-output",
        type=Path,
        default=DEFAULT_GATE_OUTPUT,
    )
    parser.add_argument(
        "--run-report",
        type=Path,
        default=DEFAULT_RUN_REPORT,
    )
    parser.add_argument(
        "--allow-single-source-degraded",
        action="store_true",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    started_at = utc_now_iso()
    steps: list[dict[str, Any]] = []

    stooq_command = [
        sys.executable,
        str(STOOQ_SCRIPT),
        "--output",
        str(args.stooq_output),
        "--log-level",
        args.log_level,
    ]

    if args.symbols_file:
        stooq_command.extend(
            ["--symbols-file", str(args.symbols_file)]
        )
    elif args.symbols:
        stooq_command.append("--symbols")
        stooq_command.extend(args.symbols)

    stooq_step = execute_step(
        "stooq_refresh",
        stooq_command,
        accepted_return_codes={0},
    )
    steps.append(stooq_step)

    if not stooq_step["successful"]:
        final_status = "blocked_at_stooq_refresh"
        write_json(
            args.run_report,
            {
                "schema_version": "1.0",
                "generated_at": utc_now_iso(),
                "started_at": started_at,
                "status": final_status,
                "canonical_files_modified": False,
                "steps": steps,
            },
        )
        return 10

    validator_command = [
        sys.executable,
        str(VALIDATOR_SCRIPT),
        "--stooq",
        str(args.stooq_output),
        "--output",
        str(args.validation_output),
        "--log-level",
        args.log_level,
    ]

    if args.yfinance:
        validator_command.extend(
            ["--yfinance", str(args.yfinance)]
        )

    validation_step = execute_step(
        "cross_source_validation",
        validator_command,
        accepted_return_codes={0},
    )
    steps.append(validation_step)

    if not validation_step["successful"]:
        final_status = "blocked_at_cross_source_validation"
        write_json(
            args.run_report,
            {
                "schema_version": "1.0",
                "generated_at": utc_now_iso(),
                "started_at": started_at,
                "status": final_status,
                "canonical_files_modified": False,
                "steps": steps,
            },
        )
        return 20

    gate_command = [
        sys.executable,
        str(GATE_SCRIPT),
        "--validation",
        str(args.validation_output),
        "--output",
        str(args.gate_output),
        "--log-level",
        args.log_level,
    ]

    if args.allow_single_source_degraded:
        gate_command.append("--allow-single-source-degraded")

    gate_step = execute_step(
        "data_quality_gate",
        gate_command,
        accepted_return_codes={0, 1, 2},
    )
    steps.append(gate_step)

    gate_payload = {}
    if args.gate_output.exists():
        gate_payload = json.loads(
            args.gate_output.read_text(encoding="utf-8")
        )

    decision = gate_payload.get("decision", "UNKNOWN")

    if decision == "PASS":
        final_status = "quality_gate_passed_promotion_disabled"
        return_code = 0
    elif decision == "WARNING":
        final_status = "quality_gate_warning"
        return_code = 1
    else:
        final_status = "quality_gate_failed"
        return_code = 2

    write_json(
        args.run_report,
        {
            "schema_version": "1.0",
            "artifact_type": (
                "offensive_equities_market_data_validation_run"
            ),
            "generated_at": utc_now_iso(),
            "started_at": started_at,
            "status": final_status,
            "quality_gate_decision": decision,
            "canonical_files_modified": False,
            "promotion_executed": False,
            "artifacts": {
                "stooq": str(args.stooq_output),
                "cross_source_validation": (
                    str(args.validation_output)
                ),
                "quality_gate": str(args.gate_output),
            },
            "steps": steps,
        },
    )

    print(
        json.dumps(
            {
                "status": final_status,
                "quality_gate_decision": decision,
                "run_report": str(args.run_report),
                "canonical_files_modified": False,
                "promotion_executed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return return_code


if __name__ == "__main__":
    sys.exit(main())
