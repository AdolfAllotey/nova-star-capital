#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Provider Provenance Report V1

Produit un rapport de traçabilité des données de marché.

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


ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive/"
    "market/providers"
)

DEFAULT_PRIMARY = ROOT / "market_data_yfinance_v1.json"
DEFAULT_SECONDARY = ROOT / "market_data_massive_v1.json"
DEFAULT_VALIDATION = ROOT / "cross_source_validation_v1.json"
DEFAULT_GATE = ROOT / "provider_quality_gate_v1.json"
DEFAULT_OUTPUT = ROOT / "provider_provenance_report_v1.json"


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


def build_report(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
    primary_path: Path,
    secondary_path: Path,
    validation_path: Path,
    gate_path: Path,
) -> dict[str, Any]:
    primary_symbols = (
        primary.get("symbols")
        if isinstance(primary.get("symbols"), dict)
        else {}
    )

    secondary_symbols = (
        secondary.get("symbols")
        if isinstance(secondary.get("symbols"), dict)
        else {}
    )

    validation_symbols = (
        validation.get("symbols")
        if isinstance(validation.get("symbols"), dict)
        else {}
    )

    symbols = sorted(
        set(primary_symbols)
        | set(secondary_symbols)
        | set(validation_symbols)
    )

    provenance: dict[str, Any] = {}

    for symbol in symbols:
        primary_row = primary_symbols.get(symbol) or {}
        secondary_row = secondary_symbols.get(symbol) or {}
        validation_row = validation_symbols.get(symbol) or {}

        provenance[symbol] = {
            "symbol": symbol,
            "primary_provider": primary.get("provider"),
            "secondary_provider": secondary.get("provider"),
            "primary_available": primary_row.get("available"),
            "secondary_available": secondary_row.get("available"),
            "primary_session_date": primary_row.get(
                "last_session_date"
            ),
            "secondary_session_date": secondary_row.get(
                "last_session_date"
            ),
            "primary_price": (
                primary_row.get("adjusted_close")
                if primary_row.get("adjusted_close") is not None
                else primary_row.get("close")
            ),
            "secondary_price": (
                secondary_row.get("adjusted_close")
                if secondary_row.get("adjusted_close") is not None
                else secondary_row.get("close")
            ),
            "validation_status": validation_row.get("status"),
            "confidence_score": validation_row.get(
                "confidence_score"
            ),
            "relative_difference_percent": (
                validation_row
                .get("prices", {})
                .get("relative_difference_percent")
            ),
            "freshness": validation_row.get("freshness"),
            "warnings": validation_row.get("warnings", []),
            "blockers": validation_row.get("blockers", []),
            "calculation_method": {
                "primary_adjustment": (
                    "auto_adjusted"
                    if primary_row.get(
                        "adjusted_price_available"
                    )
                    else "close_unqualified"
                ),
                "secondary_adjustment": (
                    "adjusted"
                    if secondary_row.get(
                        "adjusted_price_available"
                    )
                    else "close_unqualified"
                ),
                "price_averaging": False,
            },
        }

    gate_decision = gate.get("decision")
    promotion = gate.get("promotion") or {}

    return {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_market_data_provenance"
        ),
        "generated_at": utc_now_iso(),
        "status": (
            "promotion_ready"
            if gate_decision == "PASS"
            and promotion.get(
                "authorized_by_quality_gate"
            ) is True
            else "not_promotion_ready"
        ),
        "canonical_files_modified": False,
        "promotion_executed": False,
        "providers": {
            "primary": primary.get("provider"),
            "primary_status": primary.get("status"),
            "secondary": secondary.get("provider"),
            "secondary_status": secondary.get("status"),
            "secondary_configured": validation.get(
                "secondary_configured"
            ),
        },
        "quality": {
            "validation_status": validation.get("status"),
            "validation_summary": validation.get("summary"),
            "quality_gate_decision": gate_decision,
            "quality_gate_summary": gate.get("summary"),
            "promotion_authorized": promotion.get(
                "authorized_by_quality_gate",
                False,
            ),
        },
        "input_artifacts": {
            "primary": str(primary_path),
            "secondary": str(secondary_path),
            "validation": str(validation_path),
            "quality_gate": str(gate_path),
        },
        "symbols": provenance,
    }


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
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        report = build_report(
            primary=read_json(args.primary),
            secondary=read_json(args.secondary),
            validation=read_json(args.validation),
            gate=read_json(args.gate),
            primary_path=args.primary,
            secondary_path=args.secondary,
            validation_path=args.validation,
            gate_path=args.gate,
        )

        atomic_write_json(args.output, report)

        print(
            json.dumps(
                {
                    "status": report["status"],
                    "providers": report["providers"],
                    "quality": report["quality"],
                    "symbols": len(report["symbols"]),
                    "output": str(args.output),
                    "canonical_files_modified": False,
                },
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
