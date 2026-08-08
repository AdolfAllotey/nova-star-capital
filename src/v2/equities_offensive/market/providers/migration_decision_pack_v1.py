#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/nsc/data/preprod/equities_offensive")

POSITIONS_PATH = ROOT / "state/positions.json"
ACTIVE_PRICES_PATH = ROOT / "market/prices.json"

CANDIDATE_PRICES_PATH = (
    ROOT
    / "market/providers/staging/prices.candidate.json"
)

OUTPUT = (
    ROOT
    / "market/providers/migration_decision_pack_v1.json"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
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


def extract_positions(
    payload: Any,
) -> dict[str, dict[str, float | None]]:
    if not isinstance(payload, dict):
        return {}

    output: dict[str, dict[str, float | None]] = {}

    for symbol, row in payload.items():
        if not isinstance(symbol, str):
            continue

        if not isinstance(row, dict):
            continue

        quantity = safe_float(
            row.get("qty")
            if row.get("qty") is not None
            else row.get("quantity")
        )

        average_price = safe_float(
            row.get("avg_price")
            if row.get("avg_price") is not None
            else row.get("average_price")
        )

        if quantity is None or quantity <= 0:
            continue

        output[symbol.upper()] = {
            "quantity": quantity,
            "average_price": average_price,
        }

    return output


def classify_price(
    price: float | None,
) -> str:
    if price is None:
        return "missing"

    if price <= 0:
        return "corrupted_non_positive"

    if price < 0.10:
        return "corrupted_implausibly_low"

    if price > 100_000:
        return "corrupted_implausibly_high"

    return "plausible"


def calculate_valuation(
    positions: dict[str, dict[str, float | None]],
    prices: dict[str, float],
) -> dict[str, Any]:
    rows: dict[str, Any] = {}

    total_cost_basis = 0.0
    total_market_value = 0.0
    missing_prices: list[str] = []

    for symbol, position in sorted(positions.items()):
        quantity = float(
            position.get("quantity") or 0.0
        )

        average_price = position.get(
            "average_price"
        )

        market_price = prices.get(symbol)

        cost_basis = (
            quantity * float(average_price)
            if average_price is not None
            else None
        )

        market_value = (
            quantity * market_price
            if market_price is not None
            else None
        )

        unrealized_pnl = (
            market_value - cost_basis
            if market_value is not None
            and cost_basis is not None
            else None
        )

        pnl_percent = (
            unrealized_pnl / cost_basis * 100.0
            if unrealized_pnl is not None
            and cost_basis not in (None, 0)
            else None
        )

        if cost_basis is not None:
            total_cost_basis += cost_basis

        if market_value is not None:
            total_market_value += market_value
        else:
            missing_prices.append(symbol)

        rows[symbol] = {
            "quantity": quantity,
            "average_price": average_price,
            "market_price": market_price,
            "cost_basis": (
                round(cost_basis, 8)
                if cost_basis is not None
                else None
            ),
            "market_value": (
                round(market_value, 8)
                if market_value is not None
                else None
            ),
            "unrealized_pnl": (
                round(unrealized_pnl, 8)
                if unrealized_pnl is not None
                else None
            ),
            "unrealized_pnl_percent": (
                round(pnl_percent, 6)
                if pnl_percent is not None
                else None
            ),
        }

    total_pnl = (
        total_market_value - total_cost_basis
    )

    return {
        "positions": rows,
        "summary": {
            "position_count": len(positions),
            "total_cost_basis": round(
                total_cost_basis,
                8,
            ),
            "total_market_value": round(
                total_market_value,
                8,
            ),
            "total_unrealized_pnl": round(
                total_pnl,
                8,
            ),
            "missing_price_symbols": (
                missing_prices
            ),
        },
    }


def main() -> int:
    positions = extract_positions(
        read_json(POSITIONS_PATH)
    )

    active_prices = extract_prices(
        read_json(ACTIVE_PRICES_PATH)
    )

    candidate_prices = extract_prices(
        read_json(CANDIDATE_PRICES_PATH)
    )

    active_symbols = set(positions)

    all_symbols = sorted(
        set(active_prices)
        | set(candidate_prices)
    )

    corrupted_legacy_symbols: list[str] = []
    new_candidate_symbols: list[str] = []

    price_quality: dict[str, Any] = {}

    for symbol in all_symbols:
        legacy_price = active_prices.get(symbol)
        candidate_price = candidate_prices.get(symbol)

        classification = classify_price(
            legacy_price
        )

        if classification.startswith(
            "corrupted_"
        ):
            corrupted_legacy_symbols.append(
                symbol
            )

        if (
            legacy_price is None
            and candidate_price is not None
        ):
            new_candidate_symbols.append(
                symbol
            )

        price_quality[symbol] = {
            "legacy_price": legacy_price,
            "candidate_price": candidate_price,
            "legacy_classification": classification,
            "active_position": (
                symbol in active_symbols
            ),
        }

    legacy_valuation = calculate_valuation(
        positions,
        active_prices,
    )

    candidate_valuation = calculate_valuation(
        positions,
        candidate_prices,
    )

    artificial_market_value_change = (
        candidate_valuation["summary"][
            "total_market_value"
        ]
        - legacy_valuation["summary"][
            "total_market_value"
        ]
    )

    artificial_pnl_change = (
        candidate_valuation["summary"][
            "total_unrealized_pnl"
        ]
        - legacy_valuation["summary"][
            "total_unrealized_pnl"
        ]
    )

    severe_position_changes: list[str] = []

    for symbol in sorted(active_symbols):
        old_price = active_prices.get(symbol)
        new_price = candidate_prices.get(symbol)

        if (
            old_price is None
            or new_price is None
            or old_price == 0
        ):
            continue

        variation = (
            (new_price - old_price)
            / abs(old_price)
            * 100.0
        )

        if abs(variation) > 20:
            severe_position_changes.append(
                symbol
            )

    scenarios = {
        "rebase_existing_positions": {
            "recommended": False,
            "description": (
                "Conserver les quantités et remettre "
                "le prix moyen au prix réel."
            ),
            "main_risk": (
                "Réécriture artificielle de la base "
                "économique et rupture des statistiques."
            ),
        },
        "clean_restart": {
            "recommended": True,
            "description": (
                "Archiver le portefeuille simulé, "
                "neutraliser administrativement les anciennes "
                "positions et démarrer un registre vide."
            ),
            "main_advantage": (
                "Nouvelle performance mesurée depuis "
                "une base de données réelle et saine."
            ),
        },
        "legacy_isolation": {
            "recommended": False,
            "description": (
                "Conserver les anciennes positions dans "
                "un registre séparé."
            ),
            "main_risk": (
                "Complexité supplémentaire et risque "
                "de double comptage."
            ),
        },
    }

    recommendation = {
        "decision": "clean_restart",
        "confidence": "high",
        "execution_authorized": False,
        "rationale": [
            "Les positions historiques ont été valorisées avec un simulateur.",
            (
                f"{len(corrupted_legacy_symbols)} prix "
                "canoniques sont manifestement corrompus."
            ),
            (
                f"{len(severe_position_changes)} des "
                f"{len(active_symbols)} positions actives "
                "changeraient de plus de 20 %."
            ),
            (
                "La variation de P&L ne correspondrait "
                "pas à une performance réelle."
            ),
        ],
        "required_before_execution": [
            "Valider une seconde source indépendante.",
            "Obtenir un Quality Gate strict PASS.",
            "Créer une archive immuable du portefeuille legacy.",
            "Créer un rapport de clôture administrative.",
            "Définir une nouvelle date de départ de performance.",
            "Tester rollback et idempotence.",
        ],
    }

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_migration_decision_pack"
        ),
        "generated_at": utc_now_iso(),
        "status": (
            "decision_ready_execution_blocked"
        ),
        "canonical_files_modified": False,
        "positions_modified": False,
        "promotion_executed": False,
        "active_positions": {
            "count": len(positions),
            "symbols": sorted(active_symbols),
            "positions": positions,
        },
        "price_quality": {
            "corrupted_legacy_symbols": sorted(
                corrupted_legacy_symbols
            ),
            "new_candidate_symbols": sorted(
                new_candidate_symbols
            ),
            "severe_active_position_changes": (
                severe_position_changes
            ),
            "symbols": price_quality,
        },
        "valuation_comparison": {
            "legacy": legacy_valuation,
            "candidate": candidate_valuation,
            "artificial_market_value_change": round(
                artificial_market_value_change,
                8,
            ),
            "artificial_pnl_change": round(
                artificial_pnl_change,
                8,
            ),
        },
        "scenarios": scenarios,
        "recommendation": recommendation,
    }

    atomic_write_json(
        OUTPUT,
        report,
    )

    print(
        json.dumps(
            {
                "status": report["status"],
                "active_positions": report[
                    "active_positions"
                ],
                "price_quality": report[
                    "price_quality"
                ],
                "valuation_comparison": {
                    "legacy": legacy_valuation[
                        "summary"
                    ],
                    "candidate": candidate_valuation[
                        "summary"
                    ],
                    "artificial_market_value_change": (
                        report[
                            "valuation_comparison"
                        ][
                            "artificial_market_value_change"
                        ]
                    ),
                    "artificial_pnl_change": (
                        report[
                            "valuation_comparison"
                        ][
                            "artificial_pnl_change"
                        ]
                    ),
                },
                "recommendation": recommendation,
                "output": str(OUTPUT),
                "canonical_files_modified": False,
                "positions_modified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
