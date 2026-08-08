#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Provider Promotion Manager V1

Cette version est volontairement limitée au dry-run.

Elle :
- vérifie le Quality Gate ;
- construit des artefacts canoniques candidats en staging ;
- compare les candidats aux artefacts actifs ;
- refuse toute promotion réelle.

Elle ne modifie jamais :
- market/prices.json
- universe/price_snapshot.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

PROVIDER_ROOT = DATA_ROOT / "market/providers"

DEFAULT_PRIMARY = (
    PROVIDER_ROOT / "market_data_yfinance_v1.json"
)

DEFAULT_VALIDATION = (
    PROVIDER_ROOT / "cross_source_validation_v1.json"
)

DEFAULT_GATE = (
    PROVIDER_ROOT / "provider_quality_gate_v1.json"
)

DEFAULT_STAGING_DIR = (
    PROVIDER_ROOT / "staging"
)

ACTIVE_PRICES = DATA_ROOT / "market/prices.json"

ACTIVE_SNAPSHOT = (
    DATA_ROOT / "universe/price_snapshot.json"
)

DEFAULT_REPORT = (
    PROVIDER_ROOT / "promotion_dry_run_v1.json"
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


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def safe_float(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(converted):
        return None

    return converted


def extract_primary_price(
    row: dict[str, Any],
) -> float | None:
    adjusted = safe_float(row.get("adjusted_close"))

    if adjusted is not None and adjusted > 0:
        return adjusted

    close = safe_float(row.get("close"))

    if close is not None and close > 0:
        return close

    return None


def build_candidate_artifacts(
    primary: dict[str, Any],
    validation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    primary_symbols = (
        primary.get("symbols")
        if isinstance(primary.get("symbols"), dict)
        else {}
    )

    validation_symbols = (
        validation.get("symbols")
        if isinstance(validation.get("symbols"), dict)
        else {}
    )

    generated_at = utc_now_iso()

    prices: dict[str, float] = {}
    snapshot_symbols: dict[str, Any] = {}

    for symbol, row in sorted(primary_symbols.items()):
        if not isinstance(row, dict):
            continue

        price = extract_primary_price(row)

        if price is None:
            continue

        validation_row = validation_symbols.get(symbol) or {}

        prices[symbol] = round(price, 8)

        snapshot_symbols[symbol] = {
            "symbol": symbol,
            "close": round(price, 8),
            "adjusted_close": row.get("adjusted_close"),
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "volume": row.get("volume"),
            "last_session_date": row.get(
                "last_session_date"
            ),
            "ma20": row.get("ma20"),
            "ma50": row.get("ma50"),
            "ma200": row.get("ma200"),
            "high20": row.get("high20"),
            "low20": row.get("low20"),
            "return20": row.get("return20"),
            "return60": row.get("return60"),
            "return126": row.get("return126"),
            "atr14": row.get("atr14"),
            "relative_volume": row.get(
                "relative_volume"
            ),
            "average_volume20": row.get(
                "average_volume20"
            ),
            "average_dollar_volume20": row.get(
                "average_dollar_volume20"
            ),
            "source": primary.get("provider"),
            "validation_status": validation_row.get(
                "status"
            ),
            "confidence_score": validation_row.get(
                "confidence_score"
            ),
        }

    prices_candidate = {
        "ts": generated_at,
        "engine": (
            "offensive_provider_promotion_candidate_v1"
        ),
        "source": primary.get("provider"),
        "status": "staging_only",
        "canonical": False,
        "promotion_executed": False,
        "prices": prices,
    }

    snapshot_candidate = {
        "ts": generated_at,
        "engine": (
            "offensive_provider_snapshot_candidate_v1"
        ),
        "source": primary.get("provider"),
        "status": "staging_only",
        "canonical": False,
        "promotion_executed": False,
        "symbols": snapshot_symbols,
    }

    return prices_candidate, snapshot_candidate


def extract_active_prices(
    payload: dict[str, Any],
) -> dict[str, float]:
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
            price = (
                value.get("price")
                or value.get("close")
                or value.get("last")
            )
        else:
            price = value

        converted = safe_float(price)

        if converted is not None:
            output[symbol.upper()] = converted

    return output


def compare_prices(
    active: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    active_prices = extract_active_prices(active)
    candidate_prices = extract_active_prices(candidate)

    symbols = sorted(
        set(active_prices) | set(candidate_prices)
    )

    comparisons: dict[str, Any] = {}

    for symbol in symbols:
        old = active_prices.get(symbol)
        new = candidate_prices.get(symbol)

        absolute_difference = None
        relative_difference_percent = None

        if old is not None and new is not None:
            absolute_difference = abs(new - old)

            if old != 0:
                relative_difference_percent = (
                    absolute_difference / abs(old) * 100.0
                )

        comparisons[symbol] = {
            "active_price": old,
            "candidate_price": new,
            "absolute_difference": (
                round(absolute_difference, 8)
                if absolute_difference is not None
                else None
            ),
            "relative_difference_percent": (
                round(relative_difference_percent, 6)
                if relative_difference_percent
                is not None
                else None
            ),
            "active_only": (
                old is not None and new is None
            ),
            "candidate_only": (
                new is not None and old is None
            ),
        }

    return {
        "symbols_compared": len(symbols),
        "active_symbol_count": len(active_prices),
        "candidate_symbol_count": len(
            candidate_prices
        ),
        "symbols": comparisons,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--primary",
        type=Path,
        default=DEFAULT_PRIMARY,
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
        "--staging-dir",
        type=Path,
        default=DEFAULT_STAGING_DIR,
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Non pris en charge en V1. "
            "La promotion réelle est interdite."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.execute:
            raise RuntimeError(
                "La promotion réelle est interdite "
                "dans Promotion Manager V1."
            )

        primary = read_json(args.primary)
        validation = read_json(args.validation)
        gate = read_json(args.gate)

        gate_decision = gate.get("decision")
        gate_promotion = gate.get("promotion") or {}

        quality_authorized = (
            gate_decision == "PASS"
            and gate_promotion.get(
                "authorized_by_quality_gate"
            ) is True
        )

        prices_candidate, snapshot_candidate = (
            build_candidate_artifacts(
                primary=primary,
                validation=validation,
            )
        )

        args.staging_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        staged_prices = (
            args.staging_dir
            / "prices.candidate.json"
        )

        staged_snapshot = (
            args.staging_dir
            / "price_snapshot.candidate.json"
        )

        atomic_write_json(
            staged_prices,
            prices_candidate,
        )

        atomic_write_json(
            staged_snapshot,
            snapshot_candidate,
        )

        active_prices_payload = read_json(
            ACTIVE_PRICES
        )

        comparison = compare_prices(
            active=active_prices_payload,
            candidate=prices_candidate,
        )

        blockers: list[str] = []

        if not quality_authorized:
            blockers.append(
                "Le Quality Gate strict n'autorise "
                "pas la promotion."
            )

        if not prices_candidate.get("prices"):
            blockers.append(
                "Aucun prix candidat n'a été produit."
            )

        if not snapshot_candidate.get("symbols"):
            blockers.append(
                "Aucun snapshot candidat n'a été produit."
            )

        report = {
            "schema_version": "1.0",
            "artifact_type": (
                "offensive_equities_promotion_dry_run"
            ),
            "generated_at": utc_now_iso(),
            "status": (
                "dry_run_ready"
                if not blockers
                else "dry_run_blocked"
            ),
            "mode": "dry_run",
            "canonical_files_modified": False,
            "promotion_executed": False,
            "quality_gate": {
                "decision": gate_decision,
                "authorized_by_quality_gate": (
                    quality_authorized
                ),
            },
            "inputs": {
                "primary": str(args.primary),
                "validation": str(args.validation),
                "gate": str(args.gate),
            },
            "canonical_targets": {
                "prices": str(ACTIVE_PRICES),
                "price_snapshot": str(
                    ACTIVE_SNAPSHOT
                ),
            },
            "staging_artifacts": {
                "prices": str(staged_prices),
                "prices_sha256": sha256_file(
                    staged_prices
                ),
                "price_snapshot": str(
                    staged_snapshot
                ),
                "price_snapshot_sha256": (
                    sha256_file(staged_snapshot)
                ),
            },
            "active_artifacts": {
                "prices_exists": (
                    ACTIVE_PRICES.exists()
                ),
                "prices_sha256": sha256_file(
                    ACTIVE_PRICES
                ),
                "price_snapshot_exists": (
                    ACTIVE_SNAPSHOT.exists()
                ),
                "price_snapshot_sha256": (
                    sha256_file(ACTIVE_SNAPSHOT)
                ),
            },
            "comparison": comparison,
            "blockers": blockers,
        }

        atomic_write_json(args.report, report)

        print(
            json.dumps(
                {
                    "status": report["status"],
                    "mode": report["mode"],
                    "quality_gate": report[
                        "quality_gate"
                    ],
                    "staging_artifacts": report[
                        "staging_artifacts"
                    ],
                    "comparison_summary": {
                        "symbols_compared": comparison[
                            "symbols_compared"
                        ],
                        "active_symbol_count": comparison[
                            "active_symbol_count"
                        ],
                        "candidate_symbol_count": (
                            comparison[
                                "candidate_symbol_count"
                            ]
                        ),
                    },
                    "blockers": blockers,
                    "canonical_files_modified": False,
                    "promotion_executed": False,
                    "report": str(args.report),
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0 if not blockers else 1

    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                    "canonical_files_modified": False,
                    "promotion_executed": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 2


if __name__ == "__main__":
    sys.exit(main())
