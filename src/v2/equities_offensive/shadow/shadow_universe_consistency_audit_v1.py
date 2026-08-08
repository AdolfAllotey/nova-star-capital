#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Shadow Universe Consistency Audit V1

Compare :
- shortlist Nasdaq ;
- Market Data Refresher V2 ;
- Provider Layer YFinance ;
- univers filtré V2 ;
- données réellement utilisées par la chaîne shadow.

Aucune modification canonique.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/opt/nsc/data/preprod/equities_offensive")

FILES = {
    "shortlist_nasdaq": (
        ROOT / "universe/shortlist_nasdaq.json"
    ),
    "metrics_snapshot_v2": (
        ROOT / "universe/metrics_snapshot_v2.json"
    ),
    "price_snapshot_v2": (
        ROOT / "universe/price_snapshot_v2.json"
    ),
    "universe_filtered_v2": (
        ROOT / "universe/universe_filtered_v2.json"
    ),
    "provider_yfinance_v1": (
        ROOT
        / "market/providers/"
        "market_data_yfinance_v1.json"
    ),
    "shadow_signals": (
        ROOT / "shadow_v2/signals/signals_v1.json"
    ),
    "shadow_voted": (
        ROOT / "shadow_v2/voting/voted_signals.json"
    ),
    "shadow_risk": (
        ROOT / "shadow_v2/risk/risk_decisions.json"
    ),
    "shadow_candidates": (
        ROOT
        / "shadow_v2/risk/"
        "execution_candidates.json"
    ),
}

OUTPUT = (
    ROOT
    / "shadow_v2/reports/"
    "shadow_universe_consistency_audit_v1.json"
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


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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


def normalize_symbol(value: Any) -> str | None:
    if value is None:
        return None

    symbol = str(value).strip().upper()

    return symbol or None


def symbol_from_row(
    row: dict[str, Any],
) -> str | None:
    for key in (
        "symbol",
        "ticker",
        "asset",
        "instrument",
    ):
        symbol = normalize_symbol(
            row.get(key)
        )

        if symbol:
            return symbol

    return None


def extract_symbols(payload: Any) -> list[str]:
    if isinstance(payload, list):
        output: set[str] = set()

        for row in payload:
            if isinstance(row, str):
                symbol = normalize_symbol(row)
            elif isinstance(row, dict):
                symbol = symbol_from_row(row)
            else:
                symbol = None

            if symbol:
                output.add(symbol)

        return sorted(output)

    if not isinstance(payload, dict):
        return []

    for key in (
        "symbols",
        "prices",
        "metrics",
    ):
        value = payload.get(key)

        if isinstance(value, dict):
            return sorted(
                {
                    str(symbol).upper()
                    for symbol in value
                }
            )

        if isinstance(value, list):
            return extract_symbols(value)

    for key in (
        "universe",
        "signals",
        "voted",
        "voted_signals",
        "decisions",
        "risk_decisions",
        "candidates",
        "execution_candidates",
        "items",
        "data",
    ):
        value = payload.get(key)

        if isinstance(value, list):
            return extract_symbols(value)

        if isinstance(value, dict):
            output: set[str] = set()

            for symbol, row in value.items():
                normalized = normalize_symbol(symbol)

                if normalized:
                    output.add(normalized)

                if isinstance(row, dict):
                    nested = symbol_from_row(row)

                    if nested:
                        output.add(nested)

            return sorted(output)

    return []


def main() -> int:
    datasets: dict[str, Any] = {}

    for name, path in FILES.items():
        payload = read_json(path)
        symbols = extract_symbols(payload)

        datasets[name] = {
            "path": str(path),
            "exists": path.exists(),
            "root_type": (
                type(payload).__name__
                if payload is not None
                else None
            ),
            "symbols_count": len(symbols),
            "symbols": symbols,
        }

    refresher_symbols = set(
        datasets["price_snapshot_v2"]["symbols"]
    )

    provider_symbols = set(
        datasets["provider_yfinance_v1"]["symbols"]
    )

    common = sorted(
        refresher_symbols & provider_symbols
    )

    refresher_only = sorted(
        refresher_symbols - provider_symbols
    )

    provider_only = sorted(
        provider_symbols - refresher_symbols
    )

    selected = set(
        datasets["universe_filtered_v2"]["symbols"]
    )

    missing_selected_prices = sorted(
        selected - refresher_symbols
    )

    signal_symbols = set(
        datasets["shadow_signals"]["symbols"]
    )

    voted_symbols = set(
        datasets["shadow_voted"]["symbols"]
    )

    risk_symbols = set(
        datasets["shadow_risk"]["symbols"]
    )

    candidate_symbols = set(
        datasets["shadow_candidates"]["symbols"]
    )

    blockers: list[str] = []
    warnings: list[str] = []

    if missing_selected_prices:
        blockers.append(
            "Des symboles sélectionnés n'ont pas "
            "de données dans price_snapshot_v2."
        )

    if not signal_symbols.issubset(selected):
        blockers.append(
            "Le Signal Engine a produit un symbole "
            "hors de l'univers filtré V2."
        )

    if not voted_symbols.issubset(signal_symbols):
        blockers.append(
            "Le Voting Engine contient un symbole "
            "absent des signaux shadow."
        )

    if not risk_symbols.issubset(voted_symbols):
        blockers.append(
            "Le Risk Engine contient un symbole "
            "absent des votes shadow."
        )

    if not candidate_symbols.issubset(risk_symbols):
        blockers.append(
            "Les candidats d'exécution contiennent "
            "un symbole absent des décisions Risk."
        )

    if refresher_only or provider_only:
        warnings.append(
            "Le Market Data Refresher V2 et le Provider "
            "Layer YFinance n'utilisent pas exactement "
            "le même univers."
        )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_shadow_universe_consistency_audit"
        ),
        "generated_at": utc_now_iso(),
        "status": (
            "blocked"
            if blockers
            else "warning"
            if warnings
            else "healthy"
        ),
        "canonical_files_modified": False,
        "datasets": datasets,
        "provider_comparison": {
            "common_count": len(common),
            "common_symbols": common,
            "refresher_only_count": len(
                refresher_only
            ),
            "refresher_only_symbols": (
                refresher_only
            ),
            "provider_only_count": len(
                provider_only
            ),
            "provider_only_symbols": (
                provider_only
            ),
        },
        "pipeline_consistency": {
            "selected_universe": sorted(
                selected
            ),
            "selected_without_prices": (
                missing_selected_prices
            ),
            "signals": sorted(
                signal_symbols
            ),
            "voted": sorted(
                voted_symbols
            ),
            "risk_decisions": sorted(
                risk_symbols
            ),
            "execution_candidates": sorted(
                candidate_symbols
            ),
            "signal_subset_of_universe": (
                signal_symbols.issubset(
                    selected
                )
            ),
            "voted_subset_of_signals": (
                voted_symbols.issubset(
                    signal_symbols
                )
            ),
            "risk_subset_of_voted": (
                risk_symbols.issubset(
                    voted_symbols
                )
            ),
            "candidates_subset_of_risk": (
                candidate_symbols.issubset(
                    risk_symbols
                )
            ),
        },
        "blockers": blockers,
        "warnings": warnings,
    }

    atomic_write_json(
        OUTPUT,
        report,
    )

    print(
        json.dumps(
            {
                "status": report["status"],
                "provider_comparison": report[
                    "provider_comparison"
                ],
                "pipeline_consistency": report[
                    "pipeline_consistency"
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
