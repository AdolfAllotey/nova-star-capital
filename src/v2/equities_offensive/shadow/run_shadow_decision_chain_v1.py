#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Shadow Decision Chain V1

Chaîne exécutée :
- Universe V2
- Market Data V2 YFinance
- Signal Engine
- Voting Engine
- Risk Engine

Exclusions volontaires :
- Exit Engine
- Execution Plan Builder
- Broker
- Position Tracker
- Reconciliation
- UI canonique
- Reporting canonique

Aucun artefact actif ne doit être modifié.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_ROOT = Path("/opt/nsc/app")

DATA_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

SHADOW_ROOT = DATA_ROOT / "shadow_v2"

UNIVERSE_V2 = (
    DATA_ROOT / "universe/universe_filtered_v2.json"
)

PRICES_V2 = (
    DATA_ROOT / "universe/price_snapshot_v2.json"
)

RISK_INPUTS = DATA_ROOT / "inputs.json"

SHADOW_SIGNALS = (
    SHADOW_ROOT / "signals/signals_v1.json"
)

SHADOW_VOTED = (
    SHADOW_ROOT / "voting/voted_signals.json"
)

SHADOW_EXPLAIN = (
    SHADOW_ROOT / "voting/voting_explain.json"
)

SHADOW_RISK_DECISIONS = (
    SHADOW_ROOT / "risk/risk_decisions.json"
)

SHADOW_EXECUTION_CANDIDATES = (
    SHADOW_ROOT / "risk/execution_candidates.json"
)

SHADOW_REPORT = (
    SHADOW_ROOT / "reports/shadow_decision_chain_v1.json"
)

RUN_REPORT = (
    SHADOW_ROOT / "runs/shadow_decision_chain_run_v1.json"
)

SIGNAL_ENGINE = (
    APP_ROOT
    / "src/v2/equities_offensive/"
    "engines/signal_engine_v1.py"
)

VOTING_ENGINE = (
    APP_ROOT
    / "src/v2/equities_offensive/"
    "voting/voting_engine_v1.py"
)

RISK_ENGINE = (
    APP_ROOT
    / "src/v2/equities_offensive/"
    "risk/risk_engine_v1.py"
)

ACTIVE_SIGNALS = (
    DATA_ROOT / "signals/signals_v1.json"
)

ACTIVE_VOTED = (
    DATA_ROOT / "voting/voted_signals.json"
)

ACTIVE_RISK = (
    DATA_ROOT / "risk/risk_decisions.json"
)

ACTIVE_CANDIDATES = (
    DATA_ROOT / "risk/execution_candidates.json"
)

CANONICAL_WATCHLIST = [
    DATA_ROOT / "market/prices.json",
    DATA_ROOT / "universe/price_snapshot.json",
    DATA_ROOT / "universe/universe_filtered.json",
    ACTIVE_SIGNALS,
    ACTIVE_VOTED,
    ACTIVE_RISK,
    ACTIVE_CANDIDATES,
    DATA_ROOT / "risk/exit_candidates.json",
    DATA_ROOT / "execution/execution_plan.json",
    DATA_ROOT / "execution/simulated_fills.jsonl",
    DATA_ROOT / "execution/rejected_orders.jsonl",
    DATA_ROOT / "state/positions.json",
    DATA_ROOT / "state/state.json",
    DATA_ROOT / "state/exposure_snapshot.json",
    DATA_ROOT / "state/limits_report.json",
    DATA_ROOT / "state/position_report.json",
    DATA_ROOT / "state/reconciliation_report.json",
    DATA_ROOT / "ui/ui_bundle.json",
    DATA_ROOT / "reporting/dashboard_payload.json",
    DATA_ROOT / "reporting/equity_curve.json",
]


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


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def snapshot_hashes() -> dict[str, str | None]:
    return {
        str(path): sha256_file(path)
        for path in CANONICAL_WATCHLIST
    }


def run_step(
    name: str,
    command: list[str],
) -> dict[str, Any]:
    started_at = utc_now_iso()

    completed = subprocess.run(
        command,
        cwd=str(APP_ROOT),
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "NSC_ENV": "PREPROD",
            "NSC_EQU_ACTION_POLICY": "SIMULATED_ONLY",
            "NSC_OFFENSIVE_SHADOW_MODE": "1",
        },
    )

    if completed.stdout:
        print(completed.stdout, end="")

    if completed.stderr:
        print(
            completed.stderr,
            file=sys.stderr,
            end="",
        )

    return {
        "name": name,
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "command": command,
        "return_code": completed.returncode,
        "successful": completed.returncode == 0,
        "stdout_tail": completed.stdout[-6000:],
        "stderr_tail": completed.stderr[-6000:],
    }


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [
            row
            for row in payload
            if isinstance(row, dict)
        ]

    if not isinstance(payload, dict):
        return []

    for key in (
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
        candidate = payload.get(key)

        if isinstance(candidate, list):
            return [
                row
                for row in candidate
                if isinstance(row, dict)
            ]

        if isinstance(candidate, dict):
            rows: list[dict[str, Any]] = []

            for symbol, value in candidate.items():
                if not isinstance(value, dict):
                    continue

                row = dict(value)
                row.setdefault("symbol", symbol)
                rows.append(row)

            return rows

    return []


def symbol_from_row(row: dict[str, Any]) -> str | None:
    for key in (
        "symbol",
        "ticker",
        "asset",
        "instrument",
    ):
        value = row.get(key)

        if value:
            return str(value).upper()

    return None


def summarize_artifact(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    rows = extract_rows(payload)

    symbols = sorted(
        {
            symbol
            for row in rows
            if (
                symbol := symbol_from_row(row)
            )
        }
    )

    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256": sha256_file(path),
        "root_type": (
            type(payload).__name__
            if payload is not None
            else None
        ),
        "root_keys": (
            sorted(payload.keys())
            if isinstance(payload, dict)
            else []
        ),
        "row_count": len(rows),
        "symbols": symbols,
    }


def universe_symbols(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []

    symbols = payload.get("symbols")

    if isinstance(symbols, list):
        return sorted(
            {
                str(symbol).upper()
                for symbol in symbols
                if symbol
            }
        )

    universe = payload.get("universe")

    if isinstance(universe, list):
        output: set[str] = set()

        for row in universe:
            if isinstance(row, str):
                output.add(row.upper())
            elif isinstance(row, dict):
                symbol = symbol_from_row(row)

                if symbol:
                    output.add(symbol)

        return sorted(output)

    return []


def price_symbols(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []

    prices = payload.get("prices")

    if not isinstance(prices, dict):
        return []

    return sorted(
        str(symbol).upper()
        for symbol in prices
    )


def compare_symbols(
    active_path: Path,
    shadow_path: Path,
) -> dict[str, Any]:
    active = summarize_artifact(active_path)
    shadow = summarize_artifact(shadow_path)

    active_symbols = set(active["symbols"])
    shadow_symbols = set(shadow["symbols"])

    return {
        "active": active,
        "shadow": shadow,
        "common_symbols": sorted(
            active_symbols & shadow_symbols
        ),
        "shadow_only_symbols": sorted(
            shadow_symbols - active_symbols
        ),
        "active_only_symbols": sorted(
            active_symbols - shadow_symbols
        ),
    }


def main() -> int:
    started_at = utc_now_iso()

    for directory in (
        SHADOW_ROOT / "signals",
        SHADOW_ROOT / "voting",
        SHADOW_ROOT / "risk",
        SHADOW_ROOT / "reports",
        SHADOW_ROOT / "runs",
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    required_inputs = [
        UNIVERSE_V2,
        PRICES_V2,
        RISK_INPUTS,
        SIGNAL_ENGINE,
        VOTING_ENGINE,
        RISK_ENGINE,
    ]

    missing_inputs = [
        str(path)
        for path in required_inputs
        if not path.exists()
    ]

    if missing_inputs:
        report = {
            "schema_version": "1.0",
            "generated_at": utc_now_iso(),
            "status": "blocked_missing_inputs",
            "missing_inputs": missing_inputs,
            "canonical_files_modified": False,
        }

        atomic_write_json(
            RUN_REPORT,
            report,
        )

        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 2

    hashes_before = snapshot_hashes()

    steps: list[dict[str, Any]] = []

    steps.append(
        run_step(
            "signal_engine_shadow",
            [
                sys.executable,
                str(SIGNAL_ENGINE),
                "--universe",
                str(UNIVERSE_V2),
                "--prices",
                str(PRICES_V2),
                "--out",
                str(SHADOW_SIGNALS),
                "--min-score",
                "60",
            ],
        )
    )

    if steps[-1]["successful"]:
        steps.append(
            run_step(
                "voting_engine_shadow",
                [
                    sys.executable,
                    str(VOTING_ENGINE),
                    "--signals",
                    str(SHADOW_SIGNALS),
                    "--out",
                    str(SHADOW_VOTED),
                    "--explain",
                    str(SHADOW_EXPLAIN),
                    "--top-k",
                    "5",
                ],
            )
        )

    if steps[-1]["successful"]:
        steps.append(
            run_step(
                "risk_engine_shadow",
                [
                    sys.executable,
                    str(RISK_ENGINE),
                    "--voted",
                    str(SHADOW_VOTED),
                    "--inputs",
                    str(RISK_INPUTS),
                    "--out-decisions",
                    str(
                        SHADOW_RISK_DECISIONS
                    ),
                    "--out-candidates",
                    str(
                        SHADOW_EXECUTION_CANDIDATES
                    ),
                ],
            )
        )

    hashes_after = snapshot_hashes()

    changed_canonical_files = [
        path
        for path in hashes_before
        if hashes_before[path]
        != hashes_after[path]
    ]

    universe_payload = read_json(
        UNIVERSE_V2
    )

    prices_payload = read_json(
        PRICES_V2
    )

    artifacts = {
        "signals": summarize_artifact(
            SHADOW_SIGNALS
        ),
        "voted_signals": summarize_artifact(
            SHADOW_VOTED
        ),
        "voting_explain": summarize_artifact(
            SHADOW_EXPLAIN
        ),
        "risk_decisions": summarize_artifact(
            SHADOW_RISK_DECISIONS
        ),
        "execution_candidates": summarize_artifact(
            SHADOW_EXECUTION_CANDIDATES
        ),
    }

    funnel = [
        {
            "stage": "universe_v2",
            "count": len(
                universe_symbols(
                    universe_payload
                )
            ),
            "symbols": universe_symbols(
                universe_payload
            ),
        },
        {
            "stage": "market_data_v2",
            "count": len(
                price_symbols(
                    prices_payload
                )
            ),
            "symbols": price_symbols(
                prices_payload
            ),
        },
        {
            "stage": "signals",
            "count": artifacts[
                "signals"
            ]["row_count"],
            "symbols": artifacts[
                "signals"
            ]["symbols"],
        },
        {
            "stage": "voted_signals",
            "count": artifacts[
                "voted_signals"
            ]["row_count"],
            "symbols": artifacts[
                "voted_signals"
            ]["symbols"],
        },
        {
            "stage": "risk_decisions",
            "count": artifacts[
                "risk_decisions"
            ]["row_count"],
            "symbols": artifacts[
                "risk_decisions"
            ]["symbols"],
        },
        {
            "stage": "execution_candidates",
            "count": artifacts[
                "execution_candidates"
            ]["row_count"],
            "symbols": artifacts[
                "execution_candidates"
            ]["symbols"],
        },
        {
            "stage": "execution_plan",
            "count": 0,
            "symbols": [],
            "status": (
                "intentionally_not_run"
            ),
        },
    ]

    all_steps_successful = bool(steps) and all(
        step["successful"]
        for step in steps
    )

    blockers: list[str] = []

    if changed_canonical_files:
        blockers.append(
            "Des artefacts canoniques ont été modifiés."
        )

    if not all_steps_successful:
        blockers.append(
            "Au moins une étape shadow a échoué."
        )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_shadow_decision_chain"
        ),
        "generated_at": utc_now_iso(),
        "started_at": started_at,
        "status": (
            "shadow_decision_chain_completed"
            if not blockers
            else "shadow_decision_chain_blocked"
        ),
        "mode": "shadow_observation_only",
        "data_source": "yfinance_v2",
        "canonical_files_modified": bool(
            changed_canonical_files
        ),
        "execution_plan_generated": False,
        "orders_generated": False,
        "fills_generated": False,
        "positions_modified": False,
        "inputs": {
            "universe": str(UNIVERSE_V2),
            "prices": str(PRICES_V2),
            "risk_inputs": str(RISK_INPUTS),
        },
        "steps": steps,
        "artifacts": artifacts,
        "funnel": funnel,
        "active_comparison": {
            "signals": compare_symbols(
                ACTIVE_SIGNALS,
                SHADOW_SIGNALS,
            ),
            "voted_signals": compare_symbols(
                ACTIVE_VOTED,
                SHADOW_VOTED,
            ),
            "risk_decisions": compare_symbols(
                ACTIVE_RISK,
                SHADOW_RISK_DECISIONS,
            ),
            "execution_candidates": compare_symbols(
                ACTIVE_CANDIDATES,
                SHADOW_EXECUTION_CANDIDATES,
            ),
        },
        "canonical_integrity": {
            "verified_unchanged": (
                not changed_canonical_files
            ),
            "changed_files": (
                changed_canonical_files
            ),
        },
        "blockers": blockers,
        "next_boundary": {
            "execution_plan_builder": (
                "not_shadow_safe"
            ),
            "reason": (
                "Uses hard-coded canonical paths for "
                "positions, prices and output."
            ),
        },
    }

    atomic_write_json(
        SHADOW_REPORT,
        report,
    )

    run_report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_shadow_decision_chain_run"
        ),
        "generated_at": utc_now_iso(),
        "status": report["status"],
        "report": str(SHADOW_REPORT),
        "steps": steps,
        "canonical_files_modified": bool(
            changed_canonical_files
        ),
    }

    atomic_write_json(
        RUN_REPORT,
        run_report,
    )

    print(
        json.dumps(
            {
                "status": report["status"],
                "funnel": funnel,
                "canonical_integrity": report[
                    "canonical_integrity"
                ],
                "blockers": blockers,
                "report": str(SHADOW_REPORT),
                "execution_plan_generated": False,
                "orders_generated": False,
                "fills_generated": False,
                "positions_modified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if not blockers else 1


if __name__ == "__main__":
    sys.exit(main())
