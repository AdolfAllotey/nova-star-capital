#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Position & Price Migration Audit V1

Objectifs :
- comprendre le schéma réel des registres de positions ;
- identifier les positions effectivement ouvertes ;
- détecter les prix canoniques aberrants ;
- évaluer le risque de migration vers les données réelles.

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

POSITION_PATHS = [
    ROOT / "state/positions.json",
    ROOT / "state/state.json",
    ROOT / "state/positions_state.json",
    ROOT / "portfolio/positions.json",
    ROOT / "state/position_report.json",
]

ACTIVE_PRICES_PATH = ROOT / "market/prices.json"

CANDIDATE_PRICES_PATH = (
    ROOT
    / "market/providers/staging/prices.candidate.json"
)

OUTPUT = (
    ROOT
    / "market/providers/"
    "position_and_price_migration_audit_v1.json"
)

KNOWN_SYMBOLS = {
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "META",
    "NFLX",
    "GOOGL",
    "GOOG",
    "AVGO",
    "AMD",
    "TSLA",
    "CRM",
    "ORCL",
    "ADBE",
    "NOW",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_float(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(converted):
        return None

    return converted


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
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


def first_numeric(
    row: dict[str, Any],
    keys: list[str],
) -> float | None:
    for key in keys:
        if key not in row:
            continue

        converted = safe_float(row.get(key))

        if converted is not None:
            return converted

    return None


def first_text(
    row: dict[str, Any],
    keys: list[str],
) -> str | None:
    for key in keys:
        value = row.get(key)

        if value is not None and str(value).strip():
            return str(value).strip()

    return None


def looks_like_symbol(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    normalized = value.strip().upper()

    return (
        normalized in KNOWN_SYMBOLS
        or (
            1 <= len(normalized) <= 8
            and normalized.replace(".", "").replace("-", "").isalnum()
            and normalized == value.strip().upper()
        )
    )


def normalize_position(
    symbol: str,
    row: dict[str, Any],
    source_path: Path,
    json_path: str,
) -> dict[str, Any]:
    quantity = first_numeric(
        row,
        [
            "quantity",
            "qty",
            "shares",
            "position_qty",
            "net_qty",
            "current_quantity",
            "units",
            "size",
        ],
    )

    average_price = first_numeric(
        row,
        [
            "average_price",
            "avg_price",
            "average_entry_price",
            "entry_price",
            "avg_entry_price",
            "cost_basis",
        ],
    )

    market_price = first_numeric(
        row,
        [
            "market_price",
            "current_price",
            "last_price",
            "price",
            "close",
        ],
    )

    status = first_text(
        row,
        [
            "status",
            "position_status",
            "state",
        ],
    )

    explicitly_closed = (
        status is not None
        and status.lower() in {
            "closed",
            "flat",
            "inactive",
            "exited",
        }
    )

    active = (
        quantity is not None
        and quantity > 0
        and not explicitly_closed
    )

    return {
        "symbol": symbol.upper(),
        "quantity": quantity,
        "average_price": average_price,
        "market_price": market_price,
        "status": status,
        "active": active,
        "source_file": str(source_path),
        "json_path": json_path,
        "raw_keys": sorted(row.keys()),
    }


def walk_positions(
    node: Any,
    source_path: Path,
    json_path: str = "$",
) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []

    if isinstance(node, dict):
        explicit_symbol = first_text(
            node,
            [
                "symbol",
                "ticker",
                "asset",
                "instrument",
            ],
        )

        if explicit_symbol and looks_like_symbol(explicit_symbol):
            discovered.append(
                normalize_position(
                    explicit_symbol,
                    node,
                    source_path,
                    json_path,
                )
            )

        for key, value in node.items():
            child_path = f"{json_path}.{key}"

            if looks_like_symbol(key) and isinstance(value, dict):
                discovered.append(
                    normalize_position(
                        key,
                        value,
                        source_path,
                        child_path,
                    )
                )

            discovered.extend(
                walk_positions(
                    value,
                    source_path,
                    child_path,
                )
            )

    elif isinstance(node, list):
        for index, value in enumerate(node):
            discovered.extend(
                walk_positions(
                    value,
                    source_path,
                    f"{json_path}[{index}]",
                )
            )

    return discovered


def deduplicate_positions(
    positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    output: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in positions:
        identity = (
            row.get("symbol"),
            row.get("quantity"),
            row.get("average_price"),
            row.get("source_file"),
            row.get("json_path"),
        )

        output[identity] = row

    return list(output.values())


def extract_prices(payload: Any) -> dict[str, float]:
    if not isinstance(payload, dict):
        return {}

    source = (
        payload.get("prices")
        if isinstance(payload.get("prices"), dict)
        else payload
    )

    output: dict[str, float] = {}

    for symbol, row in source.items():
        if not isinstance(symbol, str):
            continue

        if isinstance(row, dict):
            raw = (
                row.get("price")
                or row.get("close")
                or row.get("adjusted_close")
                or row.get("last")
            )
        else:
            raw = row

        converted = safe_float(raw)

        if converted is not None:
            output[symbol.upper()] = converted

    return output


def classify_active_price(price: float | None) -> str:
    if price is None:
        return "missing"

    if price <= 0:
        return "non_positive"

    if price < 0.10:
        return "implausibly_low"

    if price > 100_000:
        return "implausibly_high"

    return "plausible_range"


def main() -> int:
    files: list[dict[str, Any]] = []
    all_positions: list[dict[str, Any]] = []

    for path in POSITION_PATHS:
        payload = read_json(path)

        file_report = {
            "path": str(path),
            "exists": path.exists(),
            "json_type": (
                type(payload).__name__
                if payload is not None
                else None
            ),
            "root_keys": (
                sorted(payload.keys())
                if isinstance(payload, dict)
                else []
            ),
        }

        files.append(file_report)

        if payload is not None:
            all_positions.extend(
                walk_positions(
                    payload,
                    path,
                )
            )

    all_positions = deduplicate_positions(all_positions)

    active_position_rows = [
        row
        for row in all_positions
        if row.get("active") is True
    ]

    active_position_symbols = sorted(
        {
            row["symbol"]
            for row in active_position_rows
        }
    )

    detected_symbols = sorted(
        {
            row["symbol"]
            for row in all_positions
        }
    )

    active_prices = extract_prices(
        read_json(ACTIVE_PRICES_PATH)
    )

    candidate_prices = extract_prices(
        read_json(CANDIDATE_PRICES_PATH)
    )

    price_audit: dict[str, Any] = {}
    corrupted_active_symbols: list[str] = []
    severe_migration_symbols: list[str] = []

    all_price_symbols = sorted(
        set(active_prices)
        | set(candidate_prices)
        | set(active_position_symbols)
    )

    for symbol in all_price_symbols:
        active_price = active_prices.get(symbol)
        candidate_price = candidate_prices.get(symbol)

        classification = classify_active_price(active_price)

        if classification != "plausible_range":
            corrupted_active_symbols.append(symbol)

        difference_percent = None

        if (
            active_price is not None
            and candidate_price is not None
            and active_price != 0
        ):
            difference_percent = (
                (candidate_price - active_price)
                / abs(active_price)
                * 100.0
            )

            if abs(difference_percent) > 20:
                severe_migration_symbols.append(symbol)

        price_audit[symbol] = {
            "active_price": active_price,
            "active_price_classification": classification,
            "candidate_price": candidate_price,
            "relative_difference_percent": (
                round(difference_percent, 6)
                if difference_percent is not None
                else None
            ),
            "active_position": (
                symbol in active_position_symbols
            ),
        }

    positions_missing_candidate_price = sorted(
        set(active_position_symbols)
        - set(candidate_prices)
    )

    active_positions_with_corrupted_price = sorted(
        set(active_position_symbols)
        & set(corrupted_active_symbols)
    )

    active_positions_with_severe_migration = sorted(
        set(active_position_symbols)
        & set(severe_migration_symbols)
    )

    blockers: list[str] = []
    warnings: list[str] = []

    if not active_position_symbols:
        blockers.append(
            "Aucune position active n'a été reconnue alors que "
            "l'historique de l'audit indiquait cinq positions. "
            "Le schéma doit être confirmé manuellement."
        )

    if corrupted_active_symbols:
        blockers.append(
            f"{len(corrupted_active_symbols)} prix canoniques "
            "sont absents ou manifestement aberrants."
        )

    if positions_missing_candidate_price:
        blockers.append(
            "Certaines positions actives ne disposent pas "
            "d'un prix candidat."
        )

    if active_positions_with_corrupted_price:
        blockers.append(
            "Des positions actives utilisent un prix canonique corrompu."
        )

    if active_positions_with_severe_migration:
        blockers.append(
            "Des positions actives subiraient une variation de valorisation "
            "supérieure à 20 % lors de la migration."
        )

    if severe_migration_symbols:
        warnings.append(
            f"{len(severe_migration_symbols)} symbole(s) ont un écart "
            "supérieur à 20 % entre le prix actif et le prix candidat."
        )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_position_and_price_migration_audit"
        ),
        "generated_at": utc_now_iso(),
        "status": "blocked" if blockers else "warning" if warnings else "healthy",
        "canonical_files_modified": False,
        "promotion_executed": False,
        "position_files": files,
        "position_detection": {
            "records_detected": len(all_positions),
            "detected_symbols": detected_symbols,
            "active_records": len(active_position_rows),
            "active_symbols": active_position_symbols,
            "active_positions": active_position_rows,
        },
        "price_quality": {
            "corrupted_active_symbols": sorted(
                set(corrupted_active_symbols)
            ),
            "severe_migration_symbols": sorted(
                set(severe_migration_symbols)
            ),
            "positions_missing_candidate_price": (
                positions_missing_candidate_price
            ),
            "active_positions_with_corrupted_price": (
                active_positions_with_corrupted_price
            ),
            "active_positions_with_severe_migration": (
                active_positions_with_severe_migration
            ),
        },
        "prices": price_audit,
        "blockers": blockers,
        "warnings": warnings,
    }

    atomic_write_json(OUTPUT, report)

    print(
        json.dumps(
            {
                "status": report["status"],
                "position_detection": report[
                    "position_detection"
                ],
                "price_quality": report["price_quality"],
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
