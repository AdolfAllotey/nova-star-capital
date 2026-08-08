#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Shadow Execution Plan Runner V1

Objectif :
- exécuter l'Execution Plan Builder existant ;
- isoler toutes ses lectures/écritures sensibles ;
- ne jamais appeler le broker ;
- ne jamais modifier l'état ou le plan canonique.

Le builder canonique n'est pas modifié.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_ROOT = Path("/opt/nsc/app")

DATA_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

GLOBAL_ROOT = Path(
    "/opt/nsc/data/preprod"
)

SHADOW_ROOT = DATA_ROOT / "shadow_v2"

SHADOW_EXECUTION = SHADOW_ROOT / "execution"
SHADOW_STATE = SHADOW_ROOT / "state"
SHADOW_INPUTS = SHADOW_ROOT / "inputs"
SHADOW_REPORTS = SHADOW_ROOT / "reports"

ENTRY_CANDIDATES = (
    SHADOW_ROOT
    / "risk/execution_candidates.json"
)

EXIT_CANDIDATES = (
    SHADOW_INPUTS
    / "exit_candidates.empty.json"
)

LEGACY_CANDIDATES = (
    SHADOW_INPUTS
    / "legacy_candidates.empty.json"
)

POSITIONS = (
    SHADOW_INPUTS
    / "positions.empty.json"
)

FILLS = (
    SHADOW_INPUTS
    / "simulated_fills.empty.jsonl"
)

PRICES = (
    DATA_ROOT
    / "market/providers/staging/"
    "prices.candidate.json"
)

GOVERNANCE = (
    SHADOW_INPUTS
    / "governance.shadow.json"
)

TRADING_WINDOW = (
    SHADOW_INPUTS
    / "trading_window.shadow.json"
)

PORTFOLIO_INPUT = (
    SHADOW_INPUTS
    / "portfolio_input.shadow.json"
)

PORTFOLIO_STATE = (
    SHADOW_INPUTS
    / "portfolio_state.shadow.json"
)

OUT_PLAN = (
    SHADOW_EXECUTION
    / "execution_plan.json"
)

STATE_PATH = (
    SHADOW_STATE
    / "state.json"
)

LOCK_PATH = (
    SHADOW_STATE
    / "state.lock"
)

REPORT_PATH = (
    SHADOW_REPORTS
    / "shadow_execution_plan_run_v1.json"
)

CANONICAL_GOVERNANCE = (
    DATA_ROOT
    / "governance/governance_engine_pro.json"
)

CANONICAL_TRADING_WINDOW = (
    DATA_ROOT
    / "ops/trading_window.json"
)

CANONICAL_PORTFOLIO_INPUT = (
    GLOBAL_ROOT
    / "portfolio/inputs/"
    "equities_offensive_portfolio_input.json"
)

CANONICAL_PORTFOLIO_STATE = (
    GLOBAL_ROOT
    / "portfolio/state/portfolio_state.json"
)

CANONICAL_WATCHLIST = [
    DATA_ROOT
    / "execution/execution_plan.json",

    DATA_ROOT
    / "state/state.json",

    DATA_ROOT
    / "state/positions.json",

    DATA_ROOT
    / "execution/simulated_fills.jsonl",

    DATA_ROOT
    / "execution/rejected_orders.jsonl",

    DATA_ROOT
    / "market/prices.json",

    DATA_ROOT
    / "risk/execution_candidates.json",

    DATA_ROOT
    / "risk/exit_candidates.json",

    DATA_ROOT
    / "reporting/dashboard_payload.json",

    DATA_ROOT
    / "ui/ui_bundle.json",

    GLOBAL_ROOT
    / "portfolio/state/portfolio_state.json",

    GLOBAL_ROOT
    / "portfolio/inputs/"
    "equities_offensive_portfolio_input.json",
]


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat().replace(
        "+00:00",
        "Z",
    )


def sha256_file(
    path: Path,
) -> str | None:
    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def snapshot_hashes() -> dict[str, str | None]:
    return {
        str(path): sha256_file(path)
        for path in CANONICAL_WATCHLIST
    }


def read_json(
    path: Path,
    default: Any = None,
) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return default


def atomic_write_json(
    path: Path,
    payload: Any,
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

    os.replace(
        temporary,
        path,
    )


def copy_json_source(
    source: Path,
    destination: Path,
    default: Any,
) -> None:
    payload = read_json(
        source,
        default=default,
    )

    atomic_write_json(
        destination,
        payload,
    )


def prepare_shadow_inputs() -> None:
    for directory in (
        SHADOW_EXECUTION,
        SHADOW_STATE,
        SHADOW_INPUTS,
        SHADOW_REPORTS,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    reuse_inputs = (
        os.getenv(
            "NSC_SHADOW_REUSE_INPUTS",
            "0",
        ).strip()
        == "1"
    )

    required_frozen_inputs = (
        EXIT_CANDIDATES,
        LEGACY_CANDIDATES,
        POSITIONS,
        FILLS,
        GOVERNANCE,
        TRADING_WINDOW,
        PORTFOLIO_INPUT,
        PORTFOLIO_STATE,
    )

    if (
        reuse_inputs
        and all(
            item.exists()
            for item in required_frozen_inputs
        )
    ):
        return

    atomic_write_json(
        EXIT_CANDIDATES,
        {
            "ts": utc_now_iso(),
            "candidates": [],
            "shadow": True,
        },
    )

    atomic_write_json(
        LEGACY_CANDIDATES,
        {
            "ts": utc_now_iso(),
            "candidates": [],
            "shadow": True,
        },
    )

    atomic_write_json(
        POSITIONS,
        {},
    )

    FILLS.write_text(
        "",
        encoding="utf-8",
    )

    copy_json_source(
        CANONICAL_GOVERNANCE,
        GOVERNANCE,
        {
            "mode": "PREPROD",
            "action_policy": (
                "SIMULATED_ONLY"
            ),
            "hard_block": False,
        },
    )

    governance = read_json(
        GOVERNANCE,
        {},
    )

    if not isinstance(
        governance,
        dict,
    ):
        governance = {}

    governance[
        "shadow_mode"
    ] = True

    governance[
        "action_policy"
    ] = "SIMULATED_ONLY"

    governance[
        "canonical_write_enabled"
    ] = False

    atomic_write_json(
        GOVERNANCE,
        governance,
    )

    copy_json_source(
        CANONICAL_TRADING_WINDOW,
        TRADING_WINDOW,
        {
            "is_open": False,
            "reasons": [
                "missing canonical trading window"
            ],
        },
    )

    copy_json_source(
        CANONICAL_PORTFOLIO_INPUT,
        PORTFOLIO_INPUT,
        {
            "target_weight": 0.25,
            "regime": "risk_on",
        },
    )

    copy_json_source(
        CANONICAL_PORTFOLIO_STATE,
        PORTFOLIO_STATE,
        {
            "bricks": {
                "equities_offensive": {
                    "current_exposure_eur": 0.0,
                    "target_amount_eur": 0.0,
                }
            }
        },
    )

    if not STATE_PATH.exists():
        atomic_write_json(
            STATE_PATH,
            {
                "ts": utc_now_iso(),
                "engine": (
                    "equities_shadow_state_store_v1"
                ),
                "positions": {},
                "orders_seen": [],
                "last_run": {
                    "ts": None,
                    "plan_id": None,
                    "inputs_hash": None,
                },
                "meta": {
                    "schema": 1,
                    "shadow": True,
                },
            },
        )


def validate_inputs() -> list[str]:
    required = [
        ENTRY_CANDIDATES,
        POSITIONS,
        FILLS,
        PRICES,
        GOVERNANCE,
        TRADING_WINDOW,
        PORTFOLIO_INPUT,
        PORTFOLIO_STATE,
    ]

    return [
        str(path)
        for path in required
        if not path.exists()
    ]


def extract_symbols(
    payload: Any,
    key: str,
) -> list[str]:
    if not isinstance(
        payload,
        dict,
    ):
        return []

    rows = payload.get(key)

    if not isinstance(
        rows,
        list,
    ):
        return []

    output: set[str] = set()

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        symbol = row.get("symbol")

        if symbol:
            output.add(
                str(symbol).upper()
            )

    return sorted(output)


def main() -> int:
    started_at = utc_now_iso()

    prepare_shadow_inputs()

    missing_inputs = validate_inputs()

    if missing_inputs:
        report = {
            "schema_version": "1.0",
            "generated_at": utc_now_iso(),
            "status": (
                "blocked_missing_inputs"
            ),
            "missing_inputs": missing_inputs,
            "canonical_files_modified": False,
            "execution_plan_generated": False,
        }

        atomic_write_json(
            REPORT_PATH,
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

    os.environ[
        "NSC_ENV"
    ] = "PREPROD"

    os.environ[
        "NSC_EQU_ACTION_POLICY"
    ] = "SIMULATED_ONLY"

    os.environ[
        "NSC_OFFENSIVE_SHADOW_MODE"
    ] = "1"

    module = importlib.import_module(
        "src.v2.equities_offensive."
        "execution.execution_plan_builder"
    )

    state_store_class = (
        module.StateStore
    )

    def shadow_state_store_factory():
        return state_store_class(
            state_path=STATE_PATH,
            lock_path=LOCK_PATH,
            lock_ttl_sec=120,
        )

    module.StateStore = (
        shadow_state_store_factory
    )

    module.ROOT = (
        SHADOW_ROOT
    )

    module.OUT_PATH = (
        OUT_PLAN
    )

    module.ENTRY_CANDIDATES_PATH = (
        ENTRY_CANDIDATES
    )

    module.EXIT_CANDIDATES_PATH = (
        EXIT_CANDIDATES
    )

    module.LEGACY_CANDIDATES_PATH = (
        LEGACY_CANDIDATES
    )

    module.GOV_PATH = (
        GOVERNANCE
    )

    module.TRADING_WINDOW_PATH = (
        TRADING_WINDOW
    )

    module.POSITIONS_PATH = (
        POSITIONS
    )

    module.FILLS_PATH = (
        FILLS
    )

    module.PRICES_PATH = (
        PRICES
    )

    module.PORTFOLIO_INPUT_PATH = (
        PORTFOLIO_INPUT
    )

    original_load_json = (
        module.load_json
    )

    def shadow_safe_load_json(
        path: Path,
        default: Any = None,
    ) -> Any:
        normalized = Path(path)

        canonical_portfolio_state = (
            GLOBAL_ROOT
            / "portfolio/state/"
            "portfolio_state.json"
        )

        shadow_resolved_portfolio_state = (
            SHADOW_ROOT
            / "portfolio/state/"
            "portfolio_state.json"
        )

        if normalized in {
            canonical_portfolio_state,
            shadow_resolved_portfolio_state,
        }:
            normalized = PORTFOLIO_STATE

        return original_load_json(
            normalized,
            default=default,
        )

    module.load_json = (
        shadow_safe_load_json
    )

    exception: str | None = None

    try:
        module.main()
    except Exception as exc:
        exception = (
            f"{type(exc).__name__}: {exc}"
        )

    hashes_after = snapshot_hashes()

    changed_canonical_files = [
        path
        for path in hashes_before
        if hashes_before[path]
        != hashes_after[path]
    ]

    plan = read_json(
        OUT_PLAN,
        {},
    )

    if not isinstance(
        plan,
        dict,
    ):
        plan = {}

    candidate_orders = (
        plan.get("candidate_orders")
        if isinstance(
            plan.get("candidate_orders"),
            list,
        )
        else []
    )

    orders = (
        plan.get("orders")
        if isinstance(
            plan.get("orders"),
            list,
        )
        else []
    )

    candidate_symbols = sorted(
        {
            str(row.get("symbol")).upper()
            for row in candidate_orders
            if (
                isinstance(row, dict)
                and row.get("symbol")
            )
        }
    )

    order_symbols = sorted(
        {
            str(row.get("symbol")).upper()
            for row in orders
            if (
                isinstance(row, dict)
                and row.get("symbol")
            )
        }
    )

    blockers: list[str] = []

    if exception:
        blockers.append(
            f"Builder exception: {exception}"
        )

    if changed_canonical_files:
        blockers.append(
            "Des fichiers canoniques ont été modifiés."
        )

    if not OUT_PLAN.exists():
        blockers.append(
            "Le plan shadow n'a pas été généré."
        )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_shadow_execution_plan_run"
        ),
        "generated_at": utc_now_iso(),
        "started_at": started_at,
        "status": (
            "shadow_execution_plan_completed"
            if not blockers
            else "shadow_execution_plan_blocked"
        ),
        "mode": "shadow_observation_only",
        "canonical_files_modified": bool(
            changed_canonical_files
        ),
        "positions_modified": False,
        "broker_called": False,
        "fills_generated": False,
        "inputs": {
            "entry_candidates": str(
                ENTRY_CANDIDATES
            ),
            "exit_candidates": str(
                EXIT_CANDIDATES
            ),
            "legacy_candidates": str(
                LEGACY_CANDIDATES
            ),
            "positions": str(
                POSITIONS
            ),
            "fills": str(
                FILLS
            ),
            "prices": str(
                PRICES
            ),
            "governance": str(
                GOVERNANCE
            ),
            "trading_window": str(
                TRADING_WINDOW
            ),
            "portfolio_input": str(
                PORTFOLIO_INPUT
            ),
            "portfolio_state": str(
                PORTFOLIO_STATE
            ),
            "state": str(
                STATE_PATH
            ),
            "lock": str(
                LOCK_PATH
            ),
        },
        "plan": {
            "path": str(
                OUT_PLAN
            ),
            "exists": (
                OUT_PLAN.exists()
            ),
            "engine": plan.get(
                "engine"
            ),
            "plan_id": plan.get(
                "plan_id"
            ),
            "action_policy": plan.get(
                "action_policy"
            ),
            "idempotent_skip": plan.get(
                "idempotent_skip"
            ),
            "candidate_orders_count": len(
                candidate_orders
            ),
            "candidate_symbols": (
                candidate_symbols
            ),
            "orders_count": len(
                orders
            ),
            "order_symbols": (
                order_symbols
            ),
            "reasons": plan.get(
                "reasons"
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
        "exception": exception,
        "blockers": blockers,
    }

    atomic_write_json(
        REPORT_PATH,
        report,
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if not blockers else 1


if __name__ == "__main__":
    sys.exit(main())
