#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Generic Provider Cross-Source Validator V1

Compare une source primaire à une source secondaire sans dépendre
du nom du fournisseur.

Statuts symbole :
- validated
- warning
- single_source_degraded
- blocked
- unavailable

Règles :
- aucune moyenne de prix ;
- la source primaire reste prioritaire ;
- la source secondaire valide ou déclenche un blocage ;
- aucun fichier canonique n'est modifié.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive/"
    "market/providers"
)

DEFAULT_PRIMARY = ROOT / "market_data_yfinance_v1.json"
DEFAULT_SECONDARY = ROOT / "market_data_massive_v1.json"
DEFAULT_OUTPUT = ROOT / "cross_source_validation_v1.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError(
            f"Artefact JSON invalide : {path}"
        )

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
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    os.replace(temporary, path)


def safe_float(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(converted):
        return None

    return converted


def parse_date(value: Any) -> date | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def provider_status(
    payload: dict[str, Any],
) -> str:
    return str(
        payload.get("status") or "unknown"
    ).strip().lower()


def provider_configured(
    payload: dict[str, Any],
) -> bool:
    metadata = payload.get("provider_metadata")

    if isinstance(metadata, dict):
        configured = metadata.get("configured")

        if isinstance(configured, bool):
            return configured

    return provider_status(payload) != "not_configured"


def symbol_available(
    record: Any,
) -> bool:
    if not isinstance(record, dict):
        return False

    if record.get("available") is not True:
        return False

    status = str(
        record.get("status") or ""
    ).lower()

    if status not in {"available", "healthy"}:
        return False

    price = safe_float(
        record.get("adjusted_close")
        if record.get("adjusted_close") is not None
        else record.get("close")
    )

    return price is not None and price > 0


def extract_price(
    record: dict[str, Any] | None,
) -> float | None:
    if not isinstance(record, dict):
        return None

    adjusted = safe_float(
        record.get("adjusted_close")
    )

    if adjusted is not None and adjusted > 0:
        return adjusted

    close = safe_float(record.get("close"))

    if close is not None and close > 0:
        return close

    return None


def freshness(
    session_date: Any,
    reference_date: date,
    maximum_age_days: int,
) -> dict[str, Any]:
    parsed = parse_date(session_date)

    if parsed is None:
        return {
            "status": "unknown",
            "age_calendar_days": None,
            "fresh": False,
        }

    age = (reference_date - parsed).days

    if age < 0:
        return {
            "status": "future_date",
            "age_calendar_days": age,
            "fresh": False,
        }

    return {
        "status": (
            "fresh"
            if age <= maximum_age_days
            else "stale"
        ),
        "age_calendar_days": age,
        "fresh": age <= maximum_age_days,
    }


def validate_symbol(
    symbol: str,
    primary_record: dict[str, Any] | None,
    secondary_record: dict[str, Any] | None,
    secondary_configured: bool,
    warning_threshold_percent: float,
    blocking_threshold_percent: float,
    maximum_date_gap_days: int,
    maximum_age_days: int,
    reference_date: date,
) -> dict[str, Any]:
    primary_available = symbol_available(
        primary_record
    )

    secondary_available = (
        secondary_configured
        and symbol_available(secondary_record)
    )

    primary_price = extract_price(primary_record)
    secondary_price = extract_price(
        secondary_record
    )

    primary_date = (
        primary_record.get("last_session_date")
        if isinstance(primary_record, dict)
        else None
    )

    secondary_date = (
        secondary_record.get("last_session_date")
        if isinstance(secondary_record, dict)
        else None
    )

    primary_freshness = freshness(
        primary_date,
        reference_date,
        maximum_age_days,
    )

    secondary_freshness = freshness(
        secondary_date,
        reference_date,
        maximum_age_days,
    )

    absolute_difference = None
    relative_difference = None
    relative_difference_percent = None

    if (
        primary_price is not None
        and secondary_price is not None
        and primary_price != 0
    ):
        absolute_difference = abs(
            primary_price - secondary_price
        )

        relative_difference = (
            absolute_difference / abs(primary_price)
        )

        relative_difference_percent = (
            relative_difference * 100.0
        )

    primary_parsed_date = parse_date(
        primary_date
    )
    secondary_parsed_date = parse_date(
        secondary_date
    )

    date_gap_days = None

    if (
        primary_parsed_date is not None
        and secondary_parsed_date is not None
    ):
        date_gap_days = abs(
            (
                primary_parsed_date
                - secondary_parsed_date
            ).days
        )

    reasons: list[str] = []
    warnings: list[str] = []
    blockers: list[str] = []

    if not secondary_configured:
        if (
            primary_available
            and primary_freshness["fresh"]
        ):
            status = "single_source_degraded"
            confidence = 60.0

            warnings.append(
                "La source secondaire n'est pas configurée."
            )
        else:
            status = "blocked"
            confidence = 0.0

            blockers.append(
                "La source secondaire n'est pas configurée "
                "et la source primaire n'est pas exploitable."
            )

    elif (
        not primary_available
        and not secondary_available
    ):
        status = "unavailable"
        confidence = 0.0

        blockers.append(
            "Les deux sources sont indisponibles."
        )

    elif (
        primary_available
        and not secondary_available
    ):
        if primary_freshness["fresh"]:
            status = "single_source_degraded"
            confidence = 55.0

            warnings.append(
                "La source secondaire est configurée "
                "mais indisponible pour ce symbole."
            )
        else:
            status = "blocked"
            confidence = 10.0

            blockers.append(
                "La source primaire est seule disponible "
                "et sa donnée n'est pas fraîche."
            )

    elif (
        secondary_available
        and not primary_available
    ):
        if secondary_freshness["fresh"]:
            status = "single_source_degraded"
            confidence = 45.0

            warnings.append(
                "La source primaire est indisponible ; "
                "seule la source secondaire est disponible."
            )
        else:
            status = "blocked"
            confidence = 5.0

            blockers.append(
                "La seule source disponible n'est pas fraîche."
            )

    elif (
        primary_price is None
        or secondary_price is None
    ):
        status = "blocked"
        confidence = 0.0

        blockers.append(
            "Au moins un prix est absent."
        )

    elif (
        not primary_freshness["fresh"]
        and not secondary_freshness["fresh"]
    ):
        status = "blocked"
        confidence = 10.0

        blockers.append(
            "Les deux sources sont obsolètes."
        )

    elif relative_difference_percent is None:
        status = "blocked"
        confidence = 0.0

        blockers.append(
            "L'écart relatif n'a pas pu être calculé."
        )

    elif (
        relative_difference_percent
        > blocking_threshold_percent
    ):
        status = "blocked"

        confidence = max(
            0.0,
            100.0
            - min(
                relative_difference_percent * 10.0,
                100.0,
            ),
        )

        blockers.append(
            f"Écart de "
            f"{relative_difference_percent:.4f} %, "
            f"supérieur au seuil bloquant de "
            f"{blocking_threshold_percent:.4f} %."
        )

    elif (
        date_gap_days is not None
        and date_gap_days > maximum_date_gap_days
    ):
        status = "blocked"
        confidence = 30.0

        blockers.append(
            f"Écart de dates de "
            f"{date_gap_days} jour(s), "
            f"supérieur au maximum autorisé."
        )

    elif (
        relative_difference_percent
        > warning_threshold_percent
        or not primary_freshness["fresh"]
        or not secondary_freshness["fresh"]
        or (
            date_gap_days is not None
            and date_gap_days > 0
        )
    ):
        status = "warning"

        confidence = max(
            40.0,
            100.0
            - min(
                relative_difference_percent * 8.0,
                55.0,
            ),
        )

        if (
            relative_difference_percent
            > warning_threshold_percent
        ):
            warnings.append(
                f"Écart de "
                f"{relative_difference_percent:.4f} %, "
                f"supérieur au seuil d'avertissement."
            )

        if not primary_freshness["fresh"]:
            warnings.append(
                "La donnée primaire n'est pas fraîche."
            )

        if not secondary_freshness["fresh"]:
            warnings.append(
                "La donnée secondaire n'est pas fraîche."
            )

        if date_gap_days:
            warnings.append(
                f"Les dates diffèrent de "
                f"{date_gap_days} jour(s)."
            )

    else:
        status = "validated"

        confidence = max(
            80.0,
            100.0
            - min(
                relative_difference_percent * 10.0,
                20.0,
            ),
        )

        reasons.append(
            "Les deux sources sont disponibles, "
            "fraîches et cohérentes."
        )

    reasons.extend(warnings)
    reasons.extend(blockers)

    diagnostic_hypotheses: list[str] = []

    if (
        primary_date
        and secondary_date
        and str(primary_date) != str(secondary_date)
    ):
        diagnostic_hypotheses.append(
            "Les sources ne portent pas sur "
            "la même date de séance."
        )

    if (
        relative_difference_percent is not None
        and relative_difference_percent
        > warning_threshold_percent
    ):
        diagnostic_hypotheses.extend(
            [
                "Différence de prix ajusté ou non ajusté.",
                "Split ou opération sur titre.",
                "Timing de clôture différent.",
                "Ticker ou place de cotation différente.",
                "Retard de publication d'un fournisseur.",
            ]
        )

    if not diagnostic_hypotheses:
        diagnostic_hypotheses.append(
            "Aucune cause structurelle évidente."
        )

    return {
        "symbol": symbol,
        "status": status,
        "confidence_score": round(
            confidence,
            4,
        ),
        "availability": {
            "primary": primary_available,
            "secondary": secondary_available,
            "secondary_configured": (
                secondary_configured
            ),
        },
        "dates": {
            "primary": primary_date,
            "secondary": secondary_date,
            "gap_calendar_days": date_gap_days,
        },
        "freshness": {
            "primary": primary_freshness,
            "secondary": secondary_freshness,
        },
        "prices": {
            "primary": primary_price,
            "secondary": secondary_price,
            "absolute_difference": (
                round(absolute_difference, 8)
                if absolute_difference is not None
                else None
            ),
            "relative_difference": (
                round(relative_difference, 8)
                if relative_difference is not None
                else None
            ),
            "relative_difference_percent": (
                round(
                    relative_difference_percent,
                    6,
                )
                if relative_difference_percent
                is not None
                else None
            ),
        },
        "reasons": reasons,
        "warnings": warnings,
        "blockers": blockers,
        "diagnostic_hypotheses": (
            diagnostic_hypotheses
        ),
    }


def build_report(
    primary_payload: dict[str, Any],
    secondary_payload: dict[str, Any],
    primary_path: Path,
    secondary_path: Path,
    warning_threshold_percent: float,
    blocking_threshold_percent: float,
    maximum_date_gap_days: int,
    maximum_age_days: int,
) -> dict[str, Any]:
    primary_name = str(
        primary_payload.get("provider")
        or "primary"
    )

    secondary_name = str(
        secondary_payload.get("provider")
        or "secondary"
    )

    primary_symbols = (
        primary_payload.get("symbols")
        if isinstance(
            primary_payload.get("symbols"),
            dict,
        )
        else {}
    )

    secondary_symbols = (
        secondary_payload.get("symbols")
        if isinstance(
            secondary_payload.get("symbols"),
            dict,
        )
        else {}
    )

    secondary_is_configured = provider_configured(
        secondary_payload
    )

    all_symbols = sorted(
        set(primary_symbols.keys())
        | set(secondary_symbols.keys())
    )

    if not all_symbols:
        primary_summary = (
            primary_payload.get("summary") or {}
        )

        all_symbols = sorted(
            set(
                primary_summary.get(
                    "available_symbols",
                    [],
                )
            )
            | set(
                primary_summary.get(
                    "unavailable_symbols",
                    [],
                )
            )
        )

    reference_date = datetime.now(
        timezone.utc
    ).date()

    results = {
        symbol: validate_symbol(
            symbol=symbol,
            primary_record=primary_symbols.get(
                symbol
            ),
            secondary_record=secondary_symbols.get(
                symbol
            ),
            secondary_configured=(
                secondary_is_configured
            ),
            warning_threshold_percent=(
                warning_threshold_percent
            ),
            blocking_threshold_percent=(
                blocking_threshold_percent
            ),
            maximum_date_gap_days=(
                maximum_date_gap_days
            ),
            maximum_age_days=maximum_age_days,
            reference_date=reference_date,
        )
        for symbol in all_symbols
    }

    statuses = [
        "validated",
        "warning",
        "single_source_degraded",
        "blocked",
        "unavailable",
    ]

    status_counts = {
        status: sum(
            1
            for result in results.values()
            if result["status"] == status
        )
        for status in statuses
    }

    total = len(results)

    usable_count = (
        status_counts["validated"]
        + status_counts["warning"]
        + status_counts[
            "single_source_degraded"
        ]
    )

    validated_count = status_counts["validated"]

    confidence_values = [
        float(result["confidence_score"])
        for result in results.values()
    ]

    average_confidence = (
        sum(confidence_values)
        / len(confidence_values)
        if confidence_values
        else 0.0
    )

    if (
        status_counts["blocked"] > 0
        or status_counts["unavailable"] > 0
    ):
        global_status = "blocked"

    elif status_counts[
        "single_source_degraded"
    ] > 0:
        global_status = "single_source_degraded"

    elif status_counts["warning"] > 0:
        global_status = "warning"

    elif (
        total > 0
        and status_counts["validated"] == total
    ):
        global_status = "validated"

    else:
        global_status = "unavailable"

    return {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_generic_"
            "cross_source_validation"
        ),
        "generated_at": utc_now_iso(),
        "status": global_status,
        "primary_provider": primary_name,
        "secondary_provider": secondary_name,
        "secondary_configured": (
            secondary_is_configured
        ),
        "canonical_files_modified": False,
        "promotion_executed": False,
        "price_policy": {
            "averaging_enabled": False,
            "primary_provider": primary_name,
            "secondary_role": (
                "validation_and_controlled_fallback"
            ),
        },
        "input_artifacts": {
            "primary": str(primary_path),
            "secondary": str(secondary_path),
            "primary_status": provider_status(
                primary_payload
            ),
            "secondary_status": provider_status(
                secondary_payload
            ),
        },
        "thresholds": {
            "validated_max_difference_percent": (
                warning_threshold_percent
            ),
            "warning_max_difference_percent": (
                blocking_threshold_percent
            ),
            "blocking_above_percent": (
                blocking_threshold_percent
            ),
            "maximum_date_gap_days": (
                maximum_date_gap_days
            ),
            "maximum_age_calendar_days": (
                maximum_age_days
            ),
        },
        "summary": {
            "symbols_compared": total,
            "usable_symbols": usable_count,
            "usable_percent": (
                round(
                    usable_count / total * 100.0,
                    4,
                )
                if total
                else 0.0
            ),
            "validated_symbols_count": (
                validated_count
            ),
            "validated_percent": (
                round(
                    validated_count
                    / total
                    * 100.0,
                    4,
                )
                if total
                else 0.0
            ),
            "average_confidence_score": round(
                average_confidence,
                4,
            ),
            "status_counts": status_counts,
            "validated_symbols": [
                symbol
                for symbol, result in results.items()
                if result["status"] == "validated"
            ],
            "warning_symbols": [
                symbol
                for symbol, result in results.items()
                if result["status"] == "warning"
            ],
            "single_source_degraded_symbols": [
                symbol
                for symbol, result in results.items()
                if result["status"]
                == "single_source_degraded"
            ],
            "blocked_symbols": [
                symbol
                for symbol, result in results.items()
                if result["status"] == "blocked"
            ],
            "unavailable_symbols": [
                symbol
                for symbol, result in results.items()
                if result["status"] == "unavailable"
            ],
        },
        "symbols": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validation générique de deux providers."
        )
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
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--warning-threshold-percent",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--blocking-threshold-percent",
        type=float,
        default=3.0,
    )

    parser.add_argument(
        "--maximum-date-gap-days",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--maximum-age-calendar-days",
        type=int,
        default=4,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if not args.primary.exists():
            raise FileNotFoundError(
                f"Artefact primaire absent : "
                f"{args.primary}"
            )

        if not args.secondary.exists():
            raise FileNotFoundError(
                f"Artefact secondaire absent : "
                f"{args.secondary}"
            )

        primary_payload = read_json(args.primary)
        secondary_payload = read_json(
            args.secondary
        )

        report = build_report(
            primary_payload=primary_payload,
            secondary_payload=secondary_payload,
            primary_path=args.primary,
            secondary_path=args.secondary,
            warning_threshold_percent=max(
                args.warning_threshold_percent,
                0.0,
            ),
            blocking_threshold_percent=max(
                args.blocking_threshold_percent,
                args.warning_threshold_percent,
            ),
            maximum_date_gap_days=max(
                args.maximum_date_gap_days,
                0,
            ),
            maximum_age_days=max(
                args.maximum_age_calendar_days,
                0,
            ),
        )

        atomic_write_json(
            args.output,
            report,
        )

        print(
            json.dumps(
                {
                    "status": report["status"],
                    "primary_provider": (
                        report["primary_provider"]
                    ),
                    "secondary_provider": (
                        report["secondary_provider"]
                    ),
                    "secondary_configured": (
                        report[
                            "secondary_configured"
                        ]
                    ),
                    "summary": report["summary"],
                    "output": str(args.output),
                    "canonical_files_modified": False,
                    "promotion_executed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0 if report["status"] in {
            "validated",
            "warning",
            "single_source_degraded",
        } else 1

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

        return 2


if __name__ == "__main__":
    sys.exit(main())
