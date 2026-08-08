#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Market Data Decision Funnel V1

Explique le passage :
shortlist
→ source primaire
→ source secondaire
→ validation
→ Quality Gate
→ staging
→ promotion.

Aucune écriture canonique.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

PROVIDER_ROOT = DATA_ROOT / "market/providers"

DEFAULT_SHORTLIST = (
    DATA_ROOT / "universe/shortlist_nasdaq.json"
)

DEFAULT_PRIMARY = (
    PROVIDER_ROOT / "market_data_yfinance_v1.json"
)

DEFAULT_SECONDARY = (
    PROVIDER_ROOT / "market_data_massive_v1.json"
)

DEFAULT_VALIDATION = (
    PROVIDER_ROOT / "cross_source_validation_v1.json"
)

DEFAULT_GATE = (
    PROVIDER_ROOT / "provider_quality_gate_v1.json"
)

DEFAULT_DRY_RUN = (
    PROVIDER_ROOT / "promotion_dry_run_v1.json"
)

DEFAULT_OUTPUT = (
    PROVIDER_ROOT / "market_data_decision_funnel_v1.json"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8"))

    return payload if isinstance(payload, dict) else {}


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    os.replace(temporary, path)


def count_shortlist(payload: dict[str, Any]) -> int:
    for key in (
        "symbols",
        "shortlist",
        "tickers",
        "universe",
    ):
        value = payload.get(key)

        if isinstance(value, list):
            return len(value)

        if isinstance(value, dict):
            return len(value)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--shortlist",
        type=Path,
        default=DEFAULT_SHORTLIST,
    )
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
        "--validation",
        type=Path,
        default=DEFAULT_VALIDATION,
    )
    parser.add_argument(
        "--gate",
        type=Path,
        default=DEFAULT_GATE,
    )
    parser.add_argument(
        "--dry-run",
        type=Path,
        default=DEFAULT_DRY_RUN,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    try:
        shortlist = read_json(args.shortlist)
        primary = read_json(args.primary)
        secondary = read_json(args.secondary)
        validation = read_json(args.validation)
        gate = read_json(args.gate)
        dry_run = read_json(args.dry_run)

        primary_summary = primary.get("summary") or {}
        secondary_summary = secondary.get("summary") or {}
        validation_summary = validation.get("summary") or {}
        validation_counts = (
            validation_summary.get("status_counts")
            or {}
        )

        gate_promotion = gate.get("promotion") or {}

        stages = [
            {
                "stage": "shortlist_initial",
                "count": count_shortlist(shortlist),
                "status": (
                    "available"
                    if shortlist
                    else "missing"
                ),
            },
            {
                "stage": "primary_requested",
                "count": primary_summary.get(
                    "symbols_requested",
                    0,
                ),
                "status": primary.get("status"),
            },
            {
                "stage": "primary_available",
                "count": primary_summary.get(
                    "symbols_available",
                    0,
                ),
                "status": primary.get("status"),
            },
            {
                "stage": "secondary_available",
                "count": secondary_summary.get(
                    "symbols_available",
                    0,
                ),
                "status": secondary.get("status"),
            },
            {
                "stage": "cross_source_validated",
                "count": validation_counts.get(
                    "validated",
                    0,
                ),
                "status": validation.get("status"),
            },
            {
                "stage": "cross_source_warning",
                "count": validation_counts.get(
                    "warning",
                    0,
                ),
                "status": validation.get("status"),
            },
            {
                "stage": "single_source_degraded",
                "count": validation_counts.get(
                    "single_source_degraded",
                    0,
                ),
                "status": validation.get("status"),
            },
            {
                "stage": "blocked",
                "count": validation_counts.get(
                    "blocked",
                    0,
                ),
                "status": validation.get("status"),
            },
            {
                "stage": "quality_gate",
                "count": validation_summary.get(
                    "symbols_compared",
                    0,
                ),
                "status": gate.get("decision"),
            },
            {
                "stage": "promotion_authorized",
                "count": (
                    validation_summary.get(
                        "symbols_compared",
                        0,
                    )
                    if gate_promotion.get(
                        "authorized_by_quality_gate"
                    )
                    else 0
                ),
                "status": (
                    "authorized"
                    if gate_promotion.get(
                        "authorized_by_quality_gate"
                    )
                    else "not_authorized"
                ),
            },
            {
                "stage": "staging_candidates",
                "count": (
                    dry_run
                    .get("comparison", {})
                    .get(
                        "candidate_symbol_count",
                        0,
                    )
                ),
                "status": dry_run.get("status"),
            },
            {
                "stage": "canonical_promotion",
                "count": 0,
                "status": "not_executed",
            },
        ]

        reasons: list[str] = []

        if not validation.get("secondary_configured"):
            reasons.append(
                "Source secondaire non configurée."
            )

        if gate.get("decision") != "PASS":
            reasons.append(
                "Quality Gate strict non validé."
            )

        if dry_run.get("blockers"):
            reasons.extend(dry_run["blockers"])

        report = {
            "schema_version": "1.0",
            "artifact_type": (
                "offensive_equities_market_data_decision_funnel"
            ),
            "generated_at": utc_now_iso(),
            "status": "observation_only",
            "canonical_files_modified": False,
            "promotion_executed": False,
            "stages": stages,
            "final_decision": {
                "promotion_authorized": False,
                "promotion_executed": False,
                "reasons": list(dict.fromkeys(reasons)),
            },
        }

        atomic_write_json(args.output, report)

        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

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
        return 1


if __name__ == "__main__":
    sys.exit(main())
