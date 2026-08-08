#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Market Provider Layer Runner V1

Ce runner :
- collecte YFinance ;
- collecte Massive si une clé est configurée ;
- produit des artefacts indépendants ;
- ne lance aucune validation canonique ;
- ne promeut aucun fichier ;
- ne modifie pas prices.json ;
- ne retire pas le simulateur.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from provider_base import (
    atomic_write_json,
    normalize_symbol,
    serialize_result,
    utc_now_iso,
)
from provider_registry import build_provider_registry


LOGGER = logging.getLogger(
    "nsc.offensive_market_provider_layer"
)

ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

DEFAULT_SHORTLIST_PATH = (
    ROOT / "universe/shortlist_nasdaq.json"
)

DEFAULT_OUTPUT_DIR = ROOT / "market/providers"

DEFAULT_HISTORY_DAYS = 550
DEFAULT_MINIMUM_HISTORY_ROWS = 200


def build_provider_payload(
    provider_name: str,
    provider: Any,
    symbols: list[str],
    history_days: int,
    minimum_history_rows: int,
    pause_seconds: float,
) -> dict[str, Any]:
    generated_at = utc_now_iso()

    results: dict[str, dict[str, Any]] = {}

    if not provider.is_configured():
        return {
            "schema_version": "1.0",
            "artifact_type": (
                "offensive_equities_provider_market_data"
            ),
            "generated_at": generated_at,
            "provider": provider_name,
            "provider_metadata": provider.metadata(),
            "status": "not_configured",
            "canonical_write_enabled": False,
            "summary": {
                "symbols_requested": len(symbols),
                "symbols_available": 0,
                "symbols_unavailable": len(symbols),
                "coverage_ratio": 0.0,
                "coverage_percent": 0.0,
                "available_symbols": [],
                "unavailable_symbols": symbols,
            },
            "symbols": {},
        }

    for index, symbol in enumerate(symbols):
        LOGGER.info(
            "Provider=%s symbole=%s (%s/%s)",
            provider_name,
            symbol,
            index + 1,
            len(symbols),
        )

        result = provider.fetch_symbol(
            symbol=symbol,
            history_days=history_days,
            minimum_history_rows=(
                minimum_history_rows
            ),
        )

        results[symbol] = serialize_result(result)

        if index < len(symbols) - 1:
            time.sleep(max(pause_seconds, 0.0))

    available_symbols = [
        symbol
        for symbol, result in results.items()
        if result.get("available") is True
    ]

    unavailable_symbols = [
        symbol
        for symbol, result in results.items()
        if result.get("available") is not True
    ]

    requested_count = len(symbols)
    available_count = len(available_symbols)

    coverage_ratio = (
        available_count / requested_count
        if requested_count
        else 0.0
    )

    if (
        requested_count > 0
        and available_count == requested_count
    ):
        status = "healthy"
    elif coverage_ratio >= 0.80:
        status = "degraded"
    else:
        status = "blocked"

    return {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_provider_market_data"
        ),
        "generated_at": generated_at,
        "provider": provider_name,
        "provider_metadata": provider.metadata(),
        "status": status,
        "canonical_write_enabled": False,
        "configuration": {
            "history_days": history_days,
            "minimum_history_rows": (
                minimum_history_rows
            ),
            "pause_seconds": pause_seconds,
        },
        "summary": {
            "symbols_requested": requested_count,
            "symbols_available": available_count,
            "symbols_unavailable": (
                len(unavailable_symbols)
            ),
            "coverage_ratio": round(
                coverage_ratio,
                8,
            ),
            "coverage_percent": round(
                coverage_ratio * 100.0,
                4,
            ),
            "available_symbols": available_symbols,
            "unavailable_symbols": (
                unavailable_symbols
            ),
        },
        "symbols": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exécution isolée de la Market Provider Layer."
        )
    )

    parser.add_argument(
        "--providers",
        nargs="+",
        default=[
            "yfinance",
            "massive",
        ],
    )

    parser.add_argument(
        "--shortlist",
        type=Path,
        default=DEFAULT_SHORTLIST_PATH,
        help=(
            "Shortlist autoritative utilisée lorsque "
            "--symbols n'est pas fourni."
        ),
    )

    parser.add_argument(
        "--symbols",
        nargs="*",
        help=(
            "Surcharge manuelle réservée aux tests. "
            "Par défaut, la shortlist autoritative est utilisée."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )

    parser.add_argument(
        "--history-days",
        type=int,
        default=DEFAULT_HISTORY_DAYS,
    )

    parser.add_argument(
        "--minimum-history-rows",
        type=int,
        default=DEFAULT_MINIMUM_HISTORY_ROWS,
    )

    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.25,
    )

    parser.add_argument(
        "--log-level",
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
        ],
        default="INFO",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    registry = build_provider_registry()

    universe_mode = "manual_override"
    universe_name = "manual"
    shortlist_timestamp = None

    if args.symbols:
        symbols = [
            normalize_symbol(symbol)
            for symbol in args.symbols
            if str(symbol).strip()
        ]
    else:
        universe_mode = "authoritative_shortlist"

        if not args.shortlist.exists():
            LOGGER.error(
                "Shortlist autoritative absente : %s",
                args.shortlist,
            )
            return 2

        try:
            shortlist_payload = json.loads(
                args.shortlist.read_text(
                    encoding="utf-8"
                )
            )
        except Exception as exc:
            LOGGER.error(
                "Lecture shortlist impossible : %s",
                exc,
            )
            return 2

        if not isinstance(shortlist_payload, dict):
            LOGGER.error(
                "La shortlist doit être un objet JSON."
            )
            return 2

        raw_symbols = shortlist_payload.get("symbols")

        if not isinstance(raw_symbols, list):
            LOGGER.error(
                "La shortlist ne contient pas de liste symbols."
            )
            return 2

        symbols = [
            normalize_symbol(symbol)
            for symbol in raw_symbols
            if str(symbol).strip()
        ]

        universe_name = shortlist_payload.get(
            "universe",
            "nasdaq_core",
        )

        shortlist_timestamp = shortlist_payload.get("ts")

    symbols = list(dict.fromkeys(symbols))

    if not symbols:
        LOGGER.error("Aucun symbole à traiter.")
        return 2

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_results: dict[str, Any] = {}

    for provider_name in args.providers:
        normalized_provider_name = (
            provider_name.strip().lower()
        )

        provider = registry.get(
            normalized_provider_name
        )

        if provider is None:
            run_results[normalized_provider_name] = {
                "status": "unknown_provider",
                "error": (
                    f"Provider inconnu : "
                    f"{normalized_provider_name}"
                ),
            }
            continue

        payload = build_provider_payload(
            provider_name=normalized_provider_name,
            provider=provider,
            symbols=symbols,
            history_days=max(
                args.history_days,
                30,
            ),
            minimum_history_rows=max(
                args.minimum_history_rows,
                1,
            ),
            pause_seconds=max(
                args.pause_seconds,
                0.0,
            ),
        )

        output_path = (
            args.output_dir
            / f"market_data_{normalized_provider_name}_v1.json"
        )

        atomic_write_json(
            output_path,
            payload,
        )

        run_results[normalized_provider_name] = {
            "status": payload["status"],
            "output": str(output_path),
            "summary": payload["summary"],
        }

    run_report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_provider_layer_run"
        ),
        "generated_at": utc_now_iso(),
        "status": "completed",
        "canonical_files_modified": False,
        "promotion_executed": False,
        "providers": run_results,
    }

    run_report_path = (
        args.output_dir
        / "provider_layer_run_v1.json"
    )

    atomic_write_json(
        run_report_path,
        run_report,
    )

    print(
        json.dumps(
            run_report,
            ensure_ascii=False,
            indent=2,
        )
    )

    primary_status = (
        run_results
        .get("yfinance", {})
        .get("status")
    )

    if primary_status not in {
        "healthy",
        "degraded",
    }:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
