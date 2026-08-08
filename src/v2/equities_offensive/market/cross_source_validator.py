#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Cross-Source Validator V1

Compare YFinance et Stooq sans moyenner les prix.

Statuts symbole :
- validated
- warning
- single_source_degraded
- blocked
- unavailable

Aucun artefact canonique n'est modifié.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("nsc.cross_source_validator")

DEFAULT_STOOQ_PATH = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/market_data_stooq_v1.json"
)

DEFAULT_OUTPUT = Path(
    "/opt/nsc/data/preprod/equities_offensive/market/"
    "cross_source_validation_v1.json"
)

DEFAULT_YFINANCE_CANDIDATES = [
    Path(
        "/opt/nsc/data/preprod/equities_offensive/"
        "market_data_yfinance_v2.json"
    ),
    Path(
        "/opt/nsc/data/preprod/equities_offensive/"
        "market_data_v2.json"
    ),
    Path(
        "/opt/nsc/data/preprod/equities_offensive/"
        "offensive_market_data_v2.json"
    ),
    Path(
        "/opt/nsc/data/preprod/equities_offensive/"
        "market_data_v2/market_data_yfinance_v2.json"
    ),
    Path(
        "/opt/nsc/data/preprod/equities_offensive/"
        "market_data_v2/yfinance_market_data.json"
    ),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(converted):
        return None

    return converted


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError(f"L'artefact {path} ne contient pas un objet JSON.")

    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    os.replace(temporary_path, path)


def find_yfinance_artifact(explicit_path: Path | None) -> Path:
    if explicit_path:
        if not explicit_path.exists():
            raise FileNotFoundError(
                f"Artefact YFinance introuvable : {explicit_path}"
            )
        return explicit_path

    for candidate in DEFAULT_YFINANCE_CANDIDATES:
        if candidate.exists():
            return candidate

    search_roots = [
        Path("/opt/nsc/data/preprod/equities_offensive"),
        Path("/opt/nsc/app/data/preprod/offensive_equities"),
    ]

    matches: list[Path] = []

    for root in search_roots:
        if not root.exists():
            continue

        for path in root.rglob("*.json"):
            lowered = path.name.lower()

            if (
                "yfinance" in lowered
                or (
                    "market_data" in lowered
                    and "v2" in lowered
                    and "stooq" not in lowered
                    and "validation" not in lowered
                )
            ):
                matches.append(path)

    if not matches:
        raise FileNotFoundError(
            "Aucun artefact YFinance V2 n'a été trouvé automatiquement. "
            "Utiliser --yfinance avec son chemin exact."
        )

    matches.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0]


def extract_symbol_container(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        payload.get("symbols"),
        payload.get("data"),
        payload.get("market_data"),
        payload.get("prices"),
        payload.get("results"),
    ]

    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate

    # Certains artefacts utilisent directement les tickers à la racine.
    root_candidates = {
        key: value
        for key, value in payload.items()
        if (
            isinstance(key, str)
            and isinstance(value, dict)
            and 1 <= len(key) <= 12
            and key.upper() == key
        )
    }

    if root_candidates:
        return root_candidates

    return {}


def first_present(mapping: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def extract_price(record: dict[str, Any], source: str) -> float | None:
    common_keys = [
        "adjusted_close",
        "adjustedClose",
        "adj_close",
        "adjClose",
        "price_adjusted",
        "close",
        "last_price",
        "lastPrice",
        "price",
        "current_price",
        "currentPrice",
    ]

    if source == "stooq":
        # Stooq V1 ne prétend pas que Close est ajusté.
        common_keys = [
            "adjusted_close",
            "close",
            "last_price",
            "price",
        ]

    return safe_float(first_present(record, common_keys))


def extract_date(record: dict[str, Any]) -> str | None:
    raw = first_present(
        record,
        [
            "last_session_date",
            "last_market_date",
            "market_date",
            "session_date",
            "last_date",
            "date",
            "as_of_date",
            "last_trade_date",
            "history_end",
        ],
    )

    if raw is None:
        return None

    text = str(raw).strip()

    if not text:
        return None

    if "T" in text:
        text = text.split("T", 1)[0]

    return text[:10]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def availability(record: dict[str, Any] | None) -> bool:
    if not isinstance(record, dict):
        return False

    if record.get("available") is False:
        return False

    status = str(record.get("status", "")).lower()

    if status in {"unavailable", "error", "failed", "blocked"}:
        return False

    return extract_price(record, "generic") is not None


def infer_divergence_reasons(
    yfinance_record: dict[str, Any] | None,
    stooq_record: dict[str, Any] | None,
    yfinance_date: str | None,
    stooq_date: str | None,
    relative_difference_percent: float | None,
) -> list[str]:
    reasons: list[str] = []

    if yfinance_date and stooq_date and yfinance_date != stooq_date:
        reasons.append(
            "Les sources ne portent pas sur la même date de séance."
        )

    yfinance_adjusted = first_present(
        yfinance_record or {},
        [
            "adjusted_close",
            "adjustedClose",
            "adj_close",
            "auto_adjusted",
            "adjusted",
        ],
    )

    stooq_adjusted = first_present(
        stooq_record or {},
        [
            "adjusted_close",
            "adjusted_price_available",
        ],
    )

    if yfinance_adjusted is not None and not stooq_adjusted:
        reasons.append(
            "YFinance peut utiliser un prix ajusté alors que Stooq fournit "
            "principalement un cours Close non qualifié comme ajusté."
        )

    yfinance_currency = first_present(
        yfinance_record or {},
        ["currency", "quote_currency"],
    )
    stooq_currency = first_present(
        stooq_record or {},
        ["currency", "quote_currency"],
    )

    if (
        yfinance_currency
        and stooq_currency
        and str(yfinance_currency).upper() != str(stooq_currency).upper()
    ):
        reasons.append("Les devises déclarées par les sources diffèrent.")

    if (
        relative_difference_percent is not None
        and relative_difference_percent > 3.0
    ):
        reasons.extend(
            [
                "Un split ou une opération sur titre peut ne pas être "
                "répercuté de manière identique.",
                "Le ticker ou la place de cotation peut différer entre "
                "les fournisseurs.",
                "Le timing de clôture ou de mise à jour peut être différent.",
            ]
        )

    if not reasons:
        reasons.append("Aucune cause structurelle évidente détectée.")

    return reasons


def determine_freshness(
    source_date: str | None,
    reference_date: date,
    maximum_age_calendar_days: int,
) -> dict[str, Any]:
    parsed = parse_date(source_date)

    if parsed is None:
        return {
            "status": "unknown",
            "age_calendar_days": None,
            "fresh": False,
        }

    age = (reference_date - parsed).days

    # Une date future doit être considérée comme incohérente.
    if age < 0:
        return {
            "status": "future_date",
            "age_calendar_days": age,
            "fresh": False,
        }

    return {
        "status": "fresh" if age <= maximum_age_calendar_days else "stale",
        "age_calendar_days": age,
        "fresh": age <= maximum_age_calendar_days,
    }


def validate_symbol(
    symbol: str,
    yfinance_record: dict[str, Any] | None,
    stooq_record: dict[str, Any] | None,
    warning_threshold_percent: float,
    blocking_threshold_percent: float,
    maximum_date_gap_days: int,
    maximum_age_calendar_days: int,
    reference_date: date,
) -> dict[str, Any]:
    yfinance_available = availability(yfinance_record)
    stooq_available = availability(stooq_record)

    yfinance_price = (
        extract_price(yfinance_record or {}, "yfinance")
        if yfinance_available
        else None
    )
    stooq_price = (
        extract_price(stooq_record or {}, "stooq")
        if stooq_available
        else None
    )

    yfinance_date = extract_date(yfinance_record or {})
    stooq_date = extract_date(stooq_record or {})

    yfinance_freshness = determine_freshness(
        yfinance_date,
        reference_date,
        maximum_age_calendar_days,
    )
    stooq_freshness = determine_freshness(
        stooq_date,
        reference_date,
        maximum_age_calendar_days,
    )

    absolute_difference = None
    relative_difference = None
    relative_difference_percent = None

    if (
        yfinance_price is not None
        and stooq_price is not None
        and yfinance_price != 0
    ):
        absolute_difference = abs(yfinance_price - stooq_price)
        relative_difference = absolute_difference / abs(yfinance_price)
        relative_difference_percent = relative_difference * 100.0

    yfinance_parsed_date = parse_date(yfinance_date)
    stooq_parsed_date = parse_date(stooq_date)
    date_gap_days = None

    if yfinance_parsed_date and stooq_parsed_date:
        date_gap_days = abs(
            (yfinance_parsed_date - stooq_parsed_date).days
        )

    reasons: list[str] = []
    blocking_reasons: list[str] = []
    warning_reasons: list[str] = []

    if not yfinance_available and not stooq_available:
        status = "unavailable"
        confidence = 0.0
        blocking_reasons.append("Les deux sources sont indisponibles.")

    elif yfinance_available and not stooq_available:
        if not yfinance_freshness["fresh"]:
            status = "blocked"
            confidence = 20.0
            blocking_reasons.append(
                "YFinance est la seule source disponible mais sa donnée "
                "n'est pas fraîche."
            )
        else:
            status = "single_source_degraded"
            confidence = 60.0
            warning_reasons.append(
                "Stooq est indisponible ; YFinance reste disponible."
            )

    elif stooq_available and not yfinance_available:
        if not stooq_freshness["fresh"]:
            status = "blocked"
            confidence = 15.0
            blocking_reasons.append(
                "Stooq est la seule source disponible mais sa donnée "
                "n'est pas fraîche."
            )
        else:
            status = "single_source_degraded"
            confidence = 50.0
            warning_reasons.append(
                "YFinance est indisponible ; seule la source secondaire "
                "Stooq est disponible."
            )

    elif (
        yfinance_price is None
        or stooq_price is None
        or yfinance_price <= 0
        or stooq_price <= 0
    ):
        status = "blocked"
        confidence = 0.0
        blocking_reasons.append(
            "Au moins un prix est absent, nul ou négatif."
        )

    elif (
        not yfinance_freshness["fresh"]
        and not stooq_freshness["fresh"]
    ):
        status = "blocked"
        confidence = 10.0
        blocking_reasons.append("Les deux sources sont obsolètes.")

    elif relative_difference_percent is None:
        status = "blocked"
        confidence = 0.0
        blocking_reasons.append("L'écart relatif n'a pas pu être calculé.")

    elif relative_difference_percent > blocking_threshold_percent:
        status = "blocked"
        confidence = max(
            0.0,
            100.0 - min(relative_difference_percent * 10.0, 100.0),
        )
        blocking_reasons.append(
            f"Écart cross-source de {relative_difference_percent:.4f} %, "
            f"supérieur au seuil bloquant de "
            f"{blocking_threshold_percent:.4f} %."
        )

    elif (
        date_gap_days is not None
        and date_gap_days > maximum_date_gap_days
    ):
        status = "blocked"
        confidence = 35.0
        blocking_reasons.append(
            f"Écart de dates de {date_gap_days} jours, supérieur au "
            f"maximum autorisé de {maximum_date_gap_days}."
        )

    elif (
        relative_difference_percent > warning_threshold_percent
        or not yfinance_freshness["fresh"]
        or not stooq_freshness["fresh"]
        or (date_gap_days is not None and date_gap_days > 0)
    ):
        status = "warning"

        base_confidence = (
            100.0
            - min(relative_difference_percent * 8.0, 50.0)
            if relative_difference_percent is not None
            else 50.0
        )

        confidence = max(40.0, base_confidence)

        if relative_difference_percent > warning_threshold_percent:
            warning_reasons.append(
                f"Écart cross-source de "
                f"{relative_difference_percent:.4f} %, supérieur au seuil "
                f"d'avertissement de {warning_threshold_percent:.4f} %."
            )

        if not yfinance_freshness["fresh"]:
            warning_reasons.append("La donnée YFinance n'est pas fraîche.")

        if not stooq_freshness["fresh"]:
            warning_reasons.append("La donnée Stooq n'est pas fraîche.")

        if date_gap_days:
            warning_reasons.append(
                f"Les dates de séance diffèrent de {date_gap_days} jour(s)."
            )

    else:
        status = "validated"
        confidence = max(
            80.0,
            100.0 - min(relative_difference_percent * 10.0, 20.0),
        )
        reasons.append(
            "Les deux sources sont disponibles, fraîches et cohérentes."
        )

    diagnostic_reasons = infer_divergence_reasons(
        yfinance_record,
        stooq_record,
        yfinance_date,
        stooq_date,
        relative_difference_percent,
    )

    reasons.extend(warning_reasons)
    reasons.extend(blocking_reasons)

    return {
        "symbol": symbol,
        "status": status,
        "confidence_score": round(confidence, 4),
        "availability": {
            "yfinance": yfinance_available,
            "stooq": stooq_available,
        },
        "dates": {
            "yfinance": yfinance_date,
            "stooq": stooq_date,
            "gap_calendar_days": date_gap_days,
        },
        "freshness": {
            "yfinance": yfinance_freshness,
            "stooq": stooq_freshness,
        },
        "prices": {
            "yfinance": yfinance_price,
            "stooq": stooq_price,
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
                round(relative_difference_percent, 6)
                if relative_difference_percent is not None
                else None
            ),
        },
        "reasons": reasons,
        "diagnostic_hypotheses": diagnostic_reasons,
        "blocking_reasons": blocking_reasons,
        "warning_reasons": warning_reasons,
    }


def build_report(
    yfinance_payload: dict[str, Any],
    stooq_payload: dict[str, Any],
    yfinance_path: Path,
    stooq_path: Path,
    warning_threshold_percent: float,
    blocking_threshold_percent: float,
    maximum_date_gap_days: int,
    maximum_age_calendar_days: int,
) -> dict[str, Any]:
    yfinance_symbols = extract_symbol_container(yfinance_payload)
    stooq_symbols = extract_symbol_container(stooq_payload)

    all_symbols = sorted(
        set(yfinance_symbols.keys()).union(stooq_symbols.keys())
    )

    reference_date = datetime.now(timezone.utc).date()

    validations = {
        symbol: validate_symbol(
            symbol=symbol,
            yfinance_record=yfinance_symbols.get(symbol),
            stooq_record=stooq_symbols.get(symbol),
            warning_threshold_percent=warning_threshold_percent,
            blocking_threshold_percent=blocking_threshold_percent,
            maximum_date_gap_days=maximum_date_gap_days,
            maximum_age_calendar_days=maximum_age_calendar_days,
            reference_date=reference_date,
        )
        for symbol in all_symbols
    }

    counts = {
        status: sum(
            1
            for result in validations.values()
            if result["status"] == status
        )
        for status in [
            "validated",
            "warning",
            "single_source_degraded",
            "blocked",
            "unavailable",
        ]
    }

    requested_count = len(all_symbols)
    usable_count = (
        counts["validated"]
        + counts["warning"]
        + counts["single_source_degraded"]
    )
    validated_count = counts["validated"]

    usable_ratio = usable_count / requested_count if requested_count else 0.0
    validated_ratio = (
        validated_count / requested_count if requested_count else 0.0
    )

    if counts["blocked"] > 0 or counts["unavailable"] > 0:
        overall_status = "blocked"
    elif counts["single_source_degraded"] > 0 or counts["warning"] > 0:
        overall_status = "warning"
    elif requested_count > 0 and counts["validated"] == requested_count:
        overall_status = "validated"
    else:
        overall_status = "unavailable"

    confidence_values = [
        result["confidence_score"]
        for result in validations.values()
        if isinstance(result.get("confidence_score"), (int, float))
    ]
    average_confidence = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else 0.0
    )

    return {
        "schema_version": "1.0",
        "artifact_type": "offensive_equities_cross_source_validation",
        "generated_at": utc_now_iso(),
        "status": overall_status,
        "primary_source": "yfinance",
        "secondary_source": "stooq",
        "price_policy": {
            "averaging_enabled": False,
            "primary_price_source": "yfinance",
            "secondary_source_role": "validation_and_controlled_fallback",
        },
        "input_artifacts": {
            "yfinance": str(yfinance_path),
            "stooq": str(stooq_path),
            "yfinance_generated_at": yfinance_payload.get("generated_at"),
            "stooq_generated_at": stooq_payload.get("generated_at"),
        },
        "thresholds": {
            "validated_max_difference_percent": (
                warning_threshold_percent
            ),
            "warning_max_difference_percent": (
                blocking_threshold_percent
            ),
            "blocking_difference_percent_above": (
                blocking_threshold_percent
            ),
            "maximum_date_gap_days": maximum_date_gap_days,
            "maximum_age_calendar_days": maximum_age_calendar_days,
        },
        "summary": {
            "symbols_compared": requested_count,
            "usable_symbols": usable_count,
            "usable_ratio": round(usable_ratio, 8),
            "usable_percent": round(usable_ratio * 100.0, 4),
            "validated_ratio": round(validated_ratio, 8),
            "validated_percent": round(validated_ratio * 100.0, 4),
            "average_confidence_score": round(average_confidence, 4),
            "status_counts": counts,
            "validated_symbols": [
                symbol
                for symbol, result in validations.items()
                if result["status"] == "validated"
            ],
            "warning_symbols": [
                symbol
                for symbol, result in validations.items()
                if result["status"] == "warning"
            ],
            "single_source_degraded_symbols": [
                symbol
                for symbol, result in validations.items()
                if result["status"] == "single_source_degraded"
            ],
            "blocked_symbols": [
                symbol
                for symbol, result in validations.items()
                if result["status"] == "blocked"
            ],
            "unavailable_symbols": [
                symbol
                for symbol, result in validations.items()
                if result["status"] == "unavailable"
            ],
        },
        "symbols": validations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validation indépendante YFinance versus Stooq."
    )
    parser.add_argument(
        "--yfinance",
        type=Path,
        help="Chemin exact de l'artefact YFinance V2.",
    )
    parser.add_argument(
        "--stooq",
        type=Path,
        default=DEFAULT_STOOQ_PATH,
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
        help=(
            "Tolérance calendaire. La valeur 4 absorbe notamment "
            "les week-ends sans déclarer les données obsolètes."
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
        yfinance_path = find_yfinance_artifact(args.yfinance)

        if not args.stooq.exists():
            raise FileNotFoundError(
                f"Artefact Stooq introuvable : {args.stooq}"
            )

        LOGGER.info("Artefact YFinance sélectionné : %s", yfinance_path)
        LOGGER.info("Artefact Stooq sélectionné : %s", args.stooq)

        yfinance_payload = read_json(yfinance_path)
        stooq_payload = read_json(args.stooq)

        report = build_report(
            yfinance_payload=yfinance_payload,
            stooq_payload=stooq_payload,
            yfinance_path=yfinance_path,
            stooq_path=args.stooq,
            warning_threshold_percent=max(
                args.warning_threshold_percent,
                0.0,
            ),
            blocking_threshold_percent=max(
                args.blocking_threshold_percent,
                args.warning_threshold_percent,
            ),
            maximum_date_gap_days=max(args.maximum_date_gap_days, 0),
            maximum_age_calendar_days=max(
                args.maximum_age_calendar_days,
                0,
            ),
        )

        atomic_write_json(args.output, report)

        print(
            json.dumps(
                {
                    "status": report["status"],
                    "output": str(args.output),
                    "yfinance_artifact": str(yfinance_path),
                    "stooq_artifact": str(args.stooq),
                    "summary": report["summary"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0 if report["status"] in {"validated", "warning"} else 1

    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Validation cross-source impossible : %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
