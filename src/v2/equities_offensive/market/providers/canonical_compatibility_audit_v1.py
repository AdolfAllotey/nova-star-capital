#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Canonical Compatibility Audit V1

Compare les artefacts actifs et les candidats de staging.

Aucune modification canonique.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/nsc/data/preprod/equities_offensive")

ACTIVE_PRICES = ROOT / "market/prices.json"
ACTIVE_SNAPSHOT = ROOT / "universe/price_snapshot.json"

CANDIDATE_PRICES = (
    ROOT
    / "market/providers/staging/prices.candidate.json"
)

CANDIDATE_SNAPSHOT = (
    ROOT
    / "market/providers/staging/price_snapshot.candidate.json"
)

POSITIONS_PATH = ROOT / "state/positions.json"
EXECUTION_PLAN_PATH = ROOT / "execution/execution_plan.json"
LIMITS_REPORT_PATH = ROOT / "state/limits_report.json"

OUTPUT = (
    ROOT
    / "market/providers/canonical_compatibility_audit_v1.json"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return payload if isinstance(payload, dict) else {}


def safe_float(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(converted):
        return None

    return converted


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


def extract_prices(payload: dict[str, Any]) -> dict[str, float]:
    candidate = payload.get("prices")

    if isinstance(candidate, dict):
        source = candidate
    else:
        source = payload

    output: dict[str, float] = {}

    for symbol, value in source.items():
        if not isinstance(symbol, str):
            continue

        if isinstance(value, dict):
            raw = (
                value.get("price")
                or value.get("close")
                or value.get("last")
                or value.get("adjusted_close")
            )
        else:
            raw = value

        converted = safe_float(raw)

        if converted is not None and converted > 0:
            output[symbol.upper()] = converted

    return output


def extract_snapshot_symbols(
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    for key in (
        "symbols",
        "data",
        "prices",
        "snapshot",
    ):
        candidate = payload.get(key)

        if isinstance(candidate, dict):
            return {
                str(symbol).upper(): row
                for symbol, row in candidate.items()
                if isinstance(row, dict)
            }

    return {}


def extract_position_symbols(
    payload: dict[str, Any],
) -> list[str]:
    candidates = (
        payload.get("positions")
        or payload.get("items")
        or payload.get("data")
        or []
    )

    symbols: list[str] = []

    if isinstance(candidates, dict):
        for symbol, row in candidates.items():
            quantity = None

            if isinstance(row, dict):
                quantity = (
                    row.get("quantity")
                    or row.get("qty")
                    or row.get("shares")
                )

            converted = safe_float(quantity)

            if converted is None or converted > 0:
                symbols.append(str(symbol).upper())

    elif isinstance(candidates, list):
        for row in candidates:
            if not isinstance(row, dict):
                continue

            symbol = row.get("symbol") or row.get("ticker")
            quantity = (
                row.get("quantity")
                or row.get("qty")
                or row.get("shares")
            )

            converted = safe_float(quantity)

            if symbol and (
                converted is None or converted > 0
            ):
                symbols.append(str(symbol).upper())

    return sorted(set(symbols))


def schema_signature(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "root_keys": sorted(payload.keys()),
        "has_prices_dict": isinstance(
            payload.get("prices"),
            dict,
        ),
        "has_symbols_dict": isinstance(
            payload.get("symbols"),
            dict,
        ),
        "engine": payload.get("engine"),
        "source": payload.get("source"),
        "status": payload.get("status"),
    }


def main() -> int:
    active_prices_doc = read_json(ACTIVE_PRICES)
    active_snapshot_doc = read_json(ACTIVE_SNAPSHOT)

    candidate_prices_doc = read_json(CANDIDATE_PRICES)
    candidate_snapshot_doc = read_json(
        CANDIDATE_SNAPSHOT
    )

    positions_doc = read_json(POSITIONS_PATH)
    execution_doc = read_json(EXECUTION_PLAN_PATH)
    limits_doc = read_json(LIMITS_REPORT_PATH)

    active_prices = extract_prices(active_prices_doc)
    candidate_prices = extract_prices(
        candidate_prices_doc
    )

    active_snapshot = extract_snapshot_symbols(
        active_snapshot_doc
    )
    candidate_snapshot = extract_snapshot_symbols(
        candidate_snapshot_doc
    )

    active_symbols = set(active_prices)
    candidate_symbols = set(candidate_prices)

    common_symbols = sorted(
        active_symbols & candidate_symbols
    )
    added_symbols = sorted(
        candidate_symbols - active_symbols
    )
    removed_symbols = sorted(
        active_symbols - candidate_symbols
    )

    position_symbols = extract_position_symbols(
        positions_doc
    )

    comparisons: dict[str, Any] = {}
    severe_changes: list[str] = []
    warning_changes: list[str] = []

    for symbol in sorted(
        active_symbols | candidate_symbols
    ):
        active_price = active_prices.get(symbol)
        candidate_price = candidate_prices.get(symbol)

        difference = None
        difference_percent = None

        if (
            active_price is not None
            and candidate_price is not None
        ):
            difference = candidate_price - active_price

            if active_price != 0:
                difference_percent = (
                    difference / abs(active_price) * 100.0
                )

        classification = "unchanged_or_minor"

        if difference_percent is not None:
            absolute_percent = abs(difference_percent)

            if absolute_percent > 20:
                classification = "severe_change"
                severe_changes.append(symbol)
            elif absolute_percent > 5:
                classification = "warning_change"
                warning_changes.append(symbol)

        elif active_price is None:
            classification = "new_symbol"

        elif candidate_price is None:
            classification = "removed_symbol"

        comparisons[symbol] = {
            "active_price": active_price,
            "candidate_price": candidate_price,
            "absolute_difference": (
                round(difference, 8)
                if difference is not None
                else None
            ),
            "relative_difference_percent": (
                round(difference_percent, 6)
                if difference_percent is not None
                else None
            ),
            "classification": classification,
            "open_position": symbol in position_symbols,
        }

    blockers: list[str] = []
    warnings: list[str] = []

    if removed_symbols:
        blockers.append(
            "Des symboles actifs seraient supprimés du "
            "fichier candidat."
        )

    missing_position_prices = sorted(
        set(position_symbols) - candidate_symbols
    )

    if missing_position_prices:
        blockers.append(
            "Certaines positions ouvertes ne disposent "
            "pas d'un prix candidat."
        )

    open_positions_with_severe_change = sorted(
        set(position_symbols) & set(severe_changes)
    )

    if open_positions_with_severe_change:
        blockers.append(
            "Des positions ouvertes subiraient une "
            "variation de prix supérieure à 20 %."
        )

    if severe_changes:
        warnings.append(
            f"{len(severe_changes)} symbole(s) présentent "
            "un écart supérieur à 20 % entre simulateur "
            "et données réelles."
        )

    if warning_changes:
        warnings.append(
            f"{len(warning_changes)} symbole(s) présentent "
            "un écart compris entre 5 % et 20 %."
        )

    if added_symbols:
        warnings.append(
            f"{len(added_symbols)} nouveau(x) symbole(s) "
            "seraient ajoutés au fichier canonique."
        )

    active_prices_schema = schema_signature(
        active_prices_doc
    )
    candidate_prices_schema = schema_signature(
        candidate_prices_doc
    )

    active_snapshot_schema = schema_signature(
        active_snapshot_doc
    )
    candidate_snapshot_schema = schema_signature(
        candidate_snapshot_doc
    )

    if (
        active_prices_schema["has_prices_dict"]
        != candidate_prices_schema["has_prices_dict"]
    ):
        blockers.append(
            "Le schéma du candidat prices.json ne correspond "
            "pas au schéma actif."
        )

    if (
        active_snapshot_schema["has_symbols_dict"]
        != candidate_snapshot_schema["has_symbols_dict"]
    ):
        warnings.append(
            "Le schéma racine du snapshot candidat diffère "
            "du snapshot actif."
        )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_canonical_compatibility_audit"
        ),
        "generated_at": utc_now_iso(),
        "status": (
            "blocked"
            if blockers
            else "warning"
            if warnings
            else "compatible"
        ),
        "canonical_files_modified": False,
        "promotion_executed": False,
        "artifacts": {
            "active_prices": str(ACTIVE_PRICES),
            "candidate_prices": str(CANDIDATE_PRICES),
            "active_snapshot": str(ACTIVE_SNAPSHOT),
            "candidate_snapshot": str(
                CANDIDATE_SNAPSHOT
            ),
        },
        "symbol_coverage": {
            "active_count": len(active_symbols),
            "candidate_count": len(candidate_symbols),
            "common_count": len(common_symbols),
            "added_count": len(added_symbols),
            "removed_count": len(removed_symbols),
            "common_symbols": common_symbols,
            "added_symbols": added_symbols,
            "removed_symbols": removed_symbols,
        },
        "positions": {
            "active_position_symbols": position_symbols,
            "missing_candidate_prices": (
                missing_position_prices
            ),
            "severe_price_change_positions": (
                open_positions_with_severe_change
            ),
        },
        "schema_comparison": {
            "active_prices": active_prices_schema,
            "candidate_prices": candidate_prices_schema,
            "active_snapshot": active_snapshot_schema,
            "candidate_snapshot": (
                candidate_snapshot_schema
            ),
        },
        "price_change_summary": {
            "severe_change_symbols": severe_changes,
            "warning_change_symbols": warning_changes,
        },
        "price_comparisons": comparisons,
        "runtime_context": {
            "execution_plan_present": bool(execution_doc),
            "limits_report_present": bool(limits_doc),
        },
        "blockers": blockers,
        "warnings": warnings,
    }

    atomic_write_json(OUTPUT, report)

    print(
        json.dumps(
            {
                "status": report["status"],
                "symbol_coverage": report[
                    "symbol_coverage"
                ],
                "positions": report["positions"],
                "price_change_summary": report[
                    "price_change_summary"
                ],
                "blockers": blockers,
                "warnings": warnings,
                "output": str(OUTPUT),
                "canonical_files_modified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
