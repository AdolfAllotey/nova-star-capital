#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Market Data Quality Gate V1

Le gate évalue l'artefact de validation cross-source.

Décisions :
- PASS
- WARNING
- FAIL

Cette première version est isolée et n'effectue aucune promotion canonique.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("nsc.offensive_market_data_quality_gate")

DEFAULT_VALIDATION_PATH = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/"
    "cross_source_validation_v1.json"
)

DEFAULT_OUTPUT = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/"
    "market_data_quality_gate_v1.json"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError(f"Artefact JSON invalide : {path}")

    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    os.replace(temporary_path, path)


def evaluate_gate(
    validation: dict[str, Any],
    validation_path: Path,
    minimum_usable_coverage_percent: float,
    minimum_validated_coverage_percent: float,
    maximum_warning_symbols: int,
    allow_single_source_degraded: bool,
) -> dict[str, Any]:
    summary = validation.get("summary") or {}
    status_counts = summary.get("status_counts") or {}

    symbols_compared = int(summary.get("symbols_compared") or 0)
    usable_percent = float(summary.get("usable_percent") or 0.0)
    validated_percent = float(summary.get("validated_percent") or 0.0)

    validated_count = int(status_counts.get("validated") or 0)
    warning_count = int(status_counts.get("warning") or 0)
    degraded_count = int(
        status_counts.get("single_source_degraded") or 0
    )
    blocked_count = int(status_counts.get("blocked") or 0)
    unavailable_count = int(status_counts.get("unavailable") or 0)

    controls: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    def add_control(
        control: str,
        passed: bool,
        severity: str,
        observed: Any,
        expected: Any,
        message: str,
    ) -> None:
        controls.append(
            {
                "control": control,
                "passed": passed,
                "severity": severity,
                "observed": observed,
                "expected": expected,
                "message": message,
            }
        )

        if not passed:
            if severity == "blocking":
                blockers.append(message)
            else:
                warnings.append(message)

    add_control(
        control="symbols_present",
        passed=symbols_compared > 0,
        severity="blocking",
        observed=symbols_compared,
        expected="> 0",
        message="Aucun symbole n'a été comparé.",
    )

    add_control(
        control="usable_coverage",
        passed=usable_percent >= minimum_usable_coverage_percent,
        severity="blocking",
        observed=usable_percent,
        expected=f">= {minimum_usable_coverage_percent}",
        message=(
            f"Couverture exploitable insuffisante : {usable_percent:.4f} %."
        ),
    )

    add_control(
        control="validated_coverage",
        passed=validated_percent >= minimum_validated_coverage_percent,
        severity="warning",
        observed=validated_percent,
        expected=f">= {minimum_validated_coverage_percent}",
        message=(
            f"Couverture pleinement validée sous la cible : "
            f"{validated_percent:.4f} %."
        ),
    )

    add_control(
        control="blocked_symbols",
        passed=blocked_count == 0,
        severity="blocking",
        observed=blocked_count,
        expected=0,
        message=f"{blocked_count} symbole(s) sont bloqués.",
    )

    add_control(
        control="unavailable_symbols",
        passed=unavailable_count == 0,
        severity="blocking",
        observed=unavailable_count,
        expected=0,
        message=f"{unavailable_count} symbole(s) sont indisponibles.",
    )

    add_control(
        control="warning_symbol_limit",
        passed=warning_count <= maximum_warning_symbols,
        severity="warning",
        observed=warning_count,
        expected=f"<= {maximum_warning_symbols}",
        message=(
            f"Nombre de symboles en warning supérieur au seuil : "
            f"{warning_count}."
        ),
    )

    add_control(
        control="single_source_policy",
        passed=allow_single_source_degraded or degraded_count == 0,
        severity="blocking",
        observed=degraded_count,
        expected=(
            "autorisé"
            if allow_single_source_degraded
            else "aucun symbole single_source_degraded"
        ),
        message=(
            f"{degraded_count} symbole(s) ne disposent que d'une source."
        ),
    )

    if blockers:
        decision = "FAIL"
        promotion_authorized = False
    elif warnings:
        decision = "WARNING"
        promotion_authorized = False
    else:
        decision = "PASS"
        promotion_authorized = True

    # Mesure conservatrice : même un PASS ne déclenche pas encore la promotion.
    automatic_promotion_enabled = False

    return {
        "schema_version": "1.0",
        "artifact_type": "offensive_equities_market_data_quality_gate",
        "generated_at": utc_now_iso(),
        "decision": decision,
        "status": decision.lower(),
        "promotion": {
            "authorized_by_quality_gate": promotion_authorized,
            "automatic_promotion_enabled": automatic_promotion_enabled,
            "canonical_files_modified": False,
            "message": (
                "La promotion automatique est volontairement désactivée "
                "pendant la phase de validation RC1."
            ),
        },
        "input_artifact": str(validation_path),
        "input_validation_status": validation.get("status"),
        "policy": {
            "minimum_usable_coverage_percent": (
                minimum_usable_coverage_percent
            ),
            "minimum_validated_coverage_percent": (
                minimum_validated_coverage_percent
            ),
            "maximum_warning_symbols": maximum_warning_symbols,
            "allow_single_source_degraded": (
                allow_single_source_degraded
            ),
        },
        "summary": {
            "symbols_compared": symbols_compared,
            "validated_symbols": validated_count,
            "warning_symbols": warning_count,
            "single_source_degraded_symbols": degraded_count,
            "blocked_symbols": blocked_count,
            "unavailable_symbols": unavailable_count,
            "usable_percent": usable_percent,
            "validated_percent": validated_percent,
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        "controls": controls,
        "blockers": blockers,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Data Quality Gate des actions offensives."
    )
    parser.add_argument(
        "--validation",
        type=Path,
        default=DEFAULT_VALIDATION_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--minimum-usable-coverage-percent",
        type=float,
        default=95.0,
    )
    parser.add_argument(
        "--minimum-validated-coverage-percent",
        type=float,
        default=80.0,
    )
    parser.add_argument(
        "--maximum-warning-symbols",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--allow-single-source-degraded",
        action="store_true",
        help=(
            "Autorise temporairement le statut single_source_degraded. "
            "À ne pas utiliser pour une certification stricte."
        ),
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

    try:
        if not args.validation.exists():
            raise FileNotFoundError(
                f"Rapport de validation introuvable : {args.validation}"
            )

        validation = read_json(args.validation)

        report = evaluate_gate(
            validation=validation,
            validation_path=args.validation,
            minimum_usable_coverage_percent=max(
                args.minimum_usable_coverage_percent,
                0.0,
            ),
            minimum_validated_coverage_percent=max(
                args.minimum_validated_coverage_percent,
                0.0,
            ),
            maximum_warning_symbols=max(
                args.maximum_warning_symbols,
                0,
            ),
            allow_single_source_degraded=(
                args.allow_single_source_degraded
            ),
        )

        atomic_write_json(args.output, report)

        print(
            json.dumps(
                {
                    "decision": report["decision"],
                    "output": str(args.output),
                    "promotion": report["promotion"],
                    "summary": report["summary"],
                    "blockers": report["blockers"],
                    "warnings": report["warnings"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return {
            "PASS": 0,
            "WARNING": 1,
            "FAIL": 2,
        }.get(report["decision"], 2)

    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Évaluation du quality gate impossible : %s", exc)
        return 3


if __name__ == "__main__":
    sys.exit(main())
