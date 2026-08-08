#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Generic Provider Quality Gate V1

Décisions :
- PASS
- WARNING
- FAIL

Le mode strict interdit toute promotion lorsque la source secondaire
n'est pas configurée ou lorsqu'un symbole est en source unique.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive/"
    "market/providers"
)

DEFAULT_INPUT = ROOT / "cross_source_validation_v1.json"
DEFAULT_OUTPUT = ROOT / "provider_quality_gate_v1.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Artefact JSON invalide.")

    return payload


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.replace(temporary, path)


def build_gate(
    validation: dict[str, Any],
    validation_path: Path,
    minimum_usable_percent: float,
    minimum_validated_percent: float,
    maximum_warning_symbols: int,
    strict_secondary_required: bool,
) -> dict[str, Any]:
    summary = validation.get("summary") or {}
    counts = summary.get("status_counts") or {}

    compared = int(
        summary.get("symbols_compared") or 0
    )

    usable_percent = float(
        summary.get("usable_percent") or 0.0
    )

    validated_percent = float(
        summary.get("validated_percent") or 0.0
    )

    validated = int(
        counts.get("validated") or 0
    )

    warning = int(
        counts.get("warning") or 0
    )

    degraded = int(
        counts.get("single_source_degraded")
        or 0
    )

    blocked = int(
        counts.get("blocked") or 0
    )

    unavailable = int(
        counts.get("unavailable") or 0
    )

    secondary_configured = bool(
        validation.get("secondary_configured")
    )

    controls: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    def control(
        name: str,
        passed: bool,
        severity: str,
        observed: Any,
        expected: Any,
        message: str,
    ) -> None:
        controls.append(
            {
                "control": name,
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

    control(
        "symbols_present",
        compared > 0,
        "blocking",
        compared,
        "> 0",
        "Aucun symbole n'a été évalué.",
    )

    control(
        "usable_coverage",
        usable_percent >= minimum_usable_percent,
        "blocking",
        usable_percent,
        f">= {minimum_usable_percent}",
        (
            "Couverture exploitable insuffisante : "
            f"{usable_percent:.4f} %."
        ),
    )

    control(
        "validated_coverage",
        validated_percent
        >= minimum_validated_percent,
        "warning",
        validated_percent,
        f">= {minimum_validated_percent}",
        (
            "Couverture cross-source pleinement "
            f"validée insuffisante : "
            f"{validated_percent:.4f} %."
        ),
    )

    control(
        "blocked_symbols",
        blocked == 0,
        "blocking",
        blocked,
        0,
        f"{blocked} symbole(s) bloqué(s).",
    )

    control(
        "unavailable_symbols",
        unavailable == 0,
        "blocking",
        unavailable,
        0,
        f"{unavailable} symbole(s) indisponible(s).",
    )

    control(
        "warning_limit",
        warning <= maximum_warning_symbols,
        "warning",
        warning,
        f"<= {maximum_warning_symbols}",
        (
            f"{warning} symbole(s) sont "
            "en avertissement."
        ),
    )

    control(
        "secondary_configured",
        (
            secondary_configured
            or not strict_secondary_required
        ),
        (
            "blocking"
            if strict_secondary_required
            else "warning"
        ),
        secondary_configured,
        True,
        "La source secondaire n'est pas configurée.",
    )

    control(
        "single_source_degraded",
        (
            degraded == 0
            or not strict_secondary_required
        ),
        (
            "blocking"
            if strict_secondary_required
            else "warning"
        ),
        degraded,
        0,
        (
            f"{degraded} symbole(s) ne disposent "
            "que d'une source exploitable."
        ),
    )

    if blockers:
        decision = "FAIL"
    elif warnings:
        decision = "WARNING"
    else:
        decision = "PASS"

    promotion_authorized = (
        decision == "PASS"
        and secondary_configured
        and degraded == 0
        and blocked == 0
        and unavailable == 0
    )

    return {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_provider_quality_gate"
        ),
        "generated_at": utc_now_iso(),
        "decision": decision,
        "status": decision.lower(),
        "canonical_files_modified": False,
        "promotion": {
            "authorized_by_quality_gate": (
                promotion_authorized
            ),
            "automatic_promotion_enabled": False,
            "promotion_executed": False,
            "message": (
                "La promotion automatique reste "
                "désactivée pendant l'audit RC1."
            ),
        },
        "input_artifact": str(validation_path),
        "input_status": validation.get("status"),
        "providers": {
            "primary": validation.get(
                "primary_provider"
            ),
            "secondary": validation.get(
                "secondary_provider"
            ),
            "secondary_configured": (
                secondary_configured
            ),
        },
        "policy": {
            "minimum_usable_percent": (
                minimum_usable_percent
            ),
            "minimum_validated_percent": (
                minimum_validated_percent
            ),
            "maximum_warning_symbols": (
                maximum_warning_symbols
            ),
            "strict_secondary_required": (
                strict_secondary_required
            ),
        },
        "summary": {
            "symbols_compared": compared,
            "validated_symbols": validated,
            "warning_symbols": warning,
            "single_source_degraded_symbols": (
                degraded
            ),
            "blocked_symbols": blocked,
            "unavailable_symbols": unavailable,
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
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--validation",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--minimum-usable-percent",
        type=float,
        default=95.0,
    )

    parser.add_argument(
        "--minimum-validated-percent",
        type=float,
        default=95.0,
    )

    parser.add_argument(
        "--maximum-warning-symbols",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--observation-mode",
        action="store_true",
        help=(
            "Autorise l'observation en source unique, "
            "mais interdit toujours la promotion."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        validation = read_json(
            args.validation
        )

        report = build_gate(
            validation=validation,
            validation_path=args.validation,
            minimum_usable_percent=max(
                args.minimum_usable_percent,
                0.0,
            ),
            minimum_validated_percent=max(
                args.minimum_validated_percent,
                0.0,
            ),
            maximum_warning_symbols=max(
                args.maximum_warning_symbols,
                0,
            ),
            strict_secondary_required=(
                not args.observation_mode
            ),
        )

        atomic_write_json(
            args.output,
            report,
        )

        print(
            json.dumps(
                {
                    "decision": report["decision"],
                    "summary": report["summary"],
                    "providers": report["providers"],
                    "promotion": report["promotion"],
                    "blockers": report["blockers"],
                    "warnings": report["warnings"],
                    "output": str(args.output),
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

    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 3


if __name__ == "__main__":
    sys.exit(main())
