#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Shadow End-to-End Certification V1

Chaîne certifiée :
- Universe V2
- Market Data V2
- Signal Engine
- Voting Engine
- Risk Engine
- Execution Plan Builder
- Simulated Broker
- Positions
- Exposure
- Idempotence

Toutes les écritures d'exécution sont isolées dans shadow_v2.

Aucun artefact canonique ne doit être modifié.
Aucun ordre réel ne peut être transmis.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
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
E2E_ROOT = SHADOW_ROOT / "e2e_v1"
REPORT_DIR = E2E_ROOT / "reports"

DECISION_RUNNER = (
    APP_ROOT
    / "src/v2/equities_offensive/shadow/"
    "run_shadow_decision_chain_v1.py"
)

EXECUTION_RUNNER = (
    APP_ROOT
    / "src/v2/equities_offensive/shadow/"
    "run_shadow_execution_plan_v1.py"
)

BROKER_RUNNER = (
    APP_ROOT
    / "src/v2/equities_offensive/shadow/"
    "run_shadow_simulated_broker_v1.py"
)

DECISION_REPORT = (
    SHADOW_ROOT
    / "reports/shadow_decision_chain_v1.json"
)

SHADOW_RISK_CANDIDATES = (
    SHADOW_ROOT
    / "risk/execution_candidates.json"
)

SHADOW_EXECUTION_PLAN = (
    SHADOW_ROOT
    / "execution/execution_plan.json"
)

BROKER_ROOT = SHADOW_ROOT / "broker_v1"

BROKER_PLAN = (
    BROKER_ROOT
    / "execution/execution_plan.json"
)

BROKER_FILLS = (
    BROKER_ROOT
    / "execution/simulated_fills.jsonl"
)

BROKER_REJECTIONS = (
    BROKER_ROOT
    / "execution/rejected_orders.jsonl"
)

BROKER_POSITIONS = (
    BROKER_ROOT
    / "state/positions.json"
)

BROKER_EXPOSURE = (
    BROKER_ROOT
    / "state/exposure_snapshot.json"
)

BROKER_STATE = (
    BROKER_ROOT
    / "state/state.json"
)

OUTPUT = (
    REPORT_DIR
    / "shadow_end_to_end_certification_v1.json"
)


CANONICAL_PATHS = [
    DATA_ROOT / "market/prices.json",
    DATA_ROOT / "universe/price_snapshot.json",
    DATA_ROOT / "signals/signals_v1.json",
    DATA_ROOT / "voting/voted_signals.json",
    DATA_ROOT / "risk/risk_decisions.json",
    DATA_ROOT / "risk/execution_candidates.json",
    DATA_ROOT / "execution/execution_plan.json",
    DATA_ROOT / "execution/simulated_fills.jsonl",
    DATA_ROOT / "execution/rejected_orders.jsonl",
    DATA_ROOT / "state/positions.json",
    DATA_ROOT / "state/state.json",
    DATA_ROOT / "state/exposure_snapshot.json",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def read_json(
    path: Path,
    default: Any = None,
) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return default


def write_json(
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


def sha256_file(
    path: Path,
) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def snapshot_hashes() -> dict[str, str | None]:
    return {
        str(path): sha256_file(path)
        for path in CANONICAL_PATHS
    }


def run_command(
    command: list[str],
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    process = subprocess.run(
        command,
        cwd=str(APP_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    return {
        "command": command,
        "return_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def extract_rows(
    payload: Any,
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [
            row
            for row in payload
            if isinstance(row, dict)
        ]

    if not isinstance(payload, dict):
        return []

    for key in keys:
        rows = payload.get(key)

        if isinstance(rows, list):
            return [
                row
                for row in rows
                if isinstance(row, dict)
            ]

    return []


def symbols_from_rows(
    rows: list[dict[str, Any]],
) -> list[str]:
    return sorted({
        str(row.get("symbol") or "")
        .strip()
        .upper()
        for row in rows
        if str(row.get("symbol") or "").strip()
    })


def count_jsonl(
    path: Path,
) -> int:
    if not path.exists():
        return 0

    return sum(
        1
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    )


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            row = json.loads(line)
        except Exception:
            continue

        if isinstance(row, dict):
            rows.append(row)

    return rows


def reset_shadow_execution_workspace() -> None:
    """
    Réinitialise exclusivement l'état du builder Shadow.

    Cette opération évite qu'un plan identique exécuté lors
    d'un audit précédent soit ignoré par l'idempotence.

    Aucun état canonique n'est modifié.
    """
    paths = [
        SHADOW_ROOT / "state/state.json",
        SHADOW_ROOT / "state/state.lock",
        SHADOW_ROOT / "execution/execution_plan.json",
    ]

    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    (SHADOW_ROOT / "state").mkdir(
        parents=True,
        exist_ok=True,
    )

    (SHADOW_ROOT / "execution").mkdir(
        parents=True,
        exist_ok=True,
    )


def reset_broker_workspace() -> None:
    directories = [
        BROKER_ROOT / "execution",
        BROKER_ROOT / "state",
        BROKER_ROOT / "reports",
        BROKER_ROOT / "market",
        BROKER_ROOT / "archive",
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    for path in [
        BROKER_FILLS,
        BROKER_REJECTIONS,
        BROKER_POSITIONS,
        BROKER_EXPOSURE,
        BROKER_STATE,
        BROKER_ROOT / "state/state.lock",
    ]:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    BROKER_FILLS.touch()
    BROKER_REJECTIONS.touch()

    write_json(
        BROKER_POSITIONS,
        {},
    )


def build_executable_shadow_plan(
    source_plan: dict[str, Any],
) -> dict[str, Any]:
    candidate_orders = source_plan.get(
        "candidate_orders"
    )

    if not isinstance(candidate_orders, list):
        candidate_orders = []

    normalized_orders: list[dict[str, Any]] = []

    for order in candidate_orders:
        if not isinstance(order, dict):
            continue

        symbol = str(
            order.get("symbol") or ""
        ).strip().upper()

        side = str(
            order.get("side") or ""
        ).strip().upper()

        try:
            quantity = float(
                order.get("qty") or 0.0
            )
        except Exception:
            quantity = 0.0

        if (
            not symbol
            or side not in {"BUY", "SELL"}
            or quantity <= 0
        ):
            continue

        normalized_orders.append({
            "symbol": symbol,
            "side": side,
            "qty": quantity,
            "type": order.get(
                "type",
                "MKT",
            ),
            "limit_price": order.get(
                "limit_price"
            ),
            "score": order.get("score"),
            "reason": order.get("reason"),
            "risk_notes": order.get(
                "risk_notes"
            ),
        })

    business_payload = {
        "source_plan_id": source_plan.get(
            "plan_id"
        ),
        "orders": normalized_orders,
    }

    serialized = json.dumps(
        business_payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    suffix = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:16]

    return {
        "ts": utc_now_iso(),
        "engine": (
            "shadow_end_to_end_plan_adapter_v1"
        ),
        "plan_id": f"plan_e2e_{suffix}",
        "run_id": (
            "run_e2e_"
            + datetime.now(
                timezone.utc
            ).strftime("%Y%m%dT%H%M%S%fZ")
        ),
        "action_policy": "SIMULATED_EXECUTION",
        "idempotent_skip": False,
        "candidate_orders": normalized_orders,
        "orders": normalized_orders,
        "reasons": [
            (
                "Shadow E2E execution enabled from "
                "Execution Plan Builder candidate orders."
            ),
            "No real broker is connected.",
        ],
        "audit": {
            "source_execution_plan": str(
                SHADOW_EXECUTION_PLAN
            ),
            "source_plan_id": source_plan.get(
                "plan_id"
            ),
            "source_run_id": source_plan.get(
                "run_id"
            ),
            "shadow_only": True,
        },
    }


def main() -> int:
    started_at = utc_now_iso()

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    canonical_before = snapshot_hashes()

    blockers: list[str] = []
    warnings: list[str] = []

    decision_result = run_command([
        sys.executable,
        str(DECISION_RUNNER),
    ])

    if decision_result["return_code"] != 0:
        blockers.append(
            "La chaîne de décision Shadow a échoué."
        )

    decision_report = read_json(
        DECISION_REPORT,
        {},
    ) or {}

    risk_payload = read_json(
        SHADOW_RISK_CANDIDATES,
        {},
    ) or {}

    risk_rows = extract_rows(
        risk_payload,
        (
            "candidates",
            "execution_candidates",
        ),
    )

    risk_symbols = symbols_from_rows(
        risk_rows
    )

    if not risk_rows:
        blockers.append(
            "Aucun candidat d'exécution Shadow produit."
        )

    # Certification indépendante :
    # supprimer uniquement l'historique du builder Shadow
    # afin qu'un plan déjà observé lors d'un audit antérieur
    # ne soit pas retourné en idempotent_skip.
    reset_shadow_execution_workspace()

    execution_result = run_command([
        sys.executable,
        str(EXECUTION_RUNNER),
    ])

    if execution_result["return_code"] != 0:
        blockers.append(
            "L'Execution Plan Shadow a échoué."
        )

    execution_plan = read_json(
        SHADOW_EXECUTION_PLAN,
        {},
    ) or {}

    candidate_orders = (
        execution_plan.get(
            "candidate_orders"
        )
        if isinstance(
            execution_plan.get(
                "candidate_orders"
            ),
            list,
        )
        else []
    )

    candidate_symbols = symbols_from_rows(
        [
            row
            for row in candidate_orders
            if isinstance(row, dict)
        ]
    )

    if not candidate_orders:
        blockers.append(
            "L'Execution Plan Builder ne contient "
            "aucun candidate_order."
        )

    if not set(candidate_symbols).issubset(
        set(risk_symbols)
    ):
        blockers.append(
            "Les ordres candidats ne sont pas un "
            "sous-ensemble des candidats Risk."
        )

    reset_broker_workspace()

    executable_plan = (
        build_executable_shadow_plan(
            execution_plan
        )
    )

    write_json(
        BROKER_PLAN,
        executable_plan,
    )

    fills_before = count_jsonl(
        BROKER_FILLS
    )

    broker_run_1 = run_command([
        sys.executable,
        str(BROKER_RUNNER),
    ])

    fills_after_run_1 = count_jsonl(
        BROKER_FILLS
    )

    broker_run_2 = run_command([
        sys.executable,
        str(BROKER_RUNNER),
    ])

    fills_after_run_2 = count_jsonl(
        BROKER_FILLS
    )

    fills = read_jsonl(
        BROKER_FILLS
    )

    rejections = read_jsonl(
        BROKER_REJECTIONS
    )

    positions = read_json(
        BROKER_POSITIONS,
        {},
    ) or {}

    exposure = read_json(
        BROKER_EXPOSURE,
        {},
    ) or {}

    broker_state = read_json(
        BROKER_STATE,
        {},
    ) or {}

    canonical_after = snapshot_hashes()

    changed_canonical_files = [
        path
        for path, before_hash
        in canonical_before.items()
        if canonical_after.get(path)
        != before_hash
    ]

    tests = {
        "decision_chain_completed": (
            decision_result["return_code"] == 0
            and decision_report.get("status")
            == "shadow_decision_chain_completed"
        ),
        "risk_candidates_present": (
            len(risk_rows) > 0
        ),
        "execution_plan_completed": (
            execution_result["return_code"] == 0
        ),
        "candidate_orders_present": (
            len(candidate_orders) > 0
        ),
        "execution_plan_not_skipped_on_first_run": (
            execution_plan.get("idempotent_skip") is False
        ),
        "execution_candidates_align_with_risk": (
            bool(candidate_symbols)
            and set(candidate_symbols).issubset(
                set(risk_symbols)
            )
        ),
        "broker_first_run_completed": (
            broker_run_1["return_code"] == 0
        ),
        "broker_second_run_completed": (
            broker_run_2["return_code"] == 0
        ),
        "first_run_created_expected_fills": (
            len(
                executable_plan.get(
                    "orders",
                    [],
                )
            ) > 0
            and fills_after_run_1
            - fills_before
            == len(
                executable_plan.get(
                    "orders",
                    [],
                )
            )
        ),
        "second_run_created_zero_fills": (
            fills_after_run_2
            == fills_after_run_1
        ),
        "positions_created": (
            isinstance(positions, dict)
            and len(positions) > 0
        ),
        "exposure_created": (
            isinstance(exposure, dict)
            and int(
                exposure.get(
                    "open_positions",
                    0,
                )
                or 0
            ) > 0
        ),
        "no_rejections": (
            len(rejections) == 0
        ),
        "canonical_integrity_preserved": (
            len(
                changed_canonical_files
            )
            == 0
        ),
        "real_execution_impossible": True,
    }

    failed_tests = [
        name
        for name, passed in tests.items()
        if not passed
    ]

    if broker_run_1["return_code"] != 0:
        blockers.append(
            "Le premier passage du broker Shadow "
            "a échoué."
        )

    if broker_run_2["return_code"] != 0:
        blockers.append(
            "Le second passage du broker Shadow "
            "a échoué."
        )

    if changed_canonical_files:
        blockers.append(
            "Au moins un artefact canonique a été "
            "modifié pendant la certification."
        )

    if rejections:
        warnings.append(
            f"{len(rejections)} rejet(s) ont été "
            "enregistrés par le broker Shadow."
        )

    status = (
        "PASS"
        if not blockers
        and not failed_tests
        else "FAIL"
    )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_shadow_end_to_end_"
            "certification"
        ),
        "generated_at": utc_now_iso(),
        "started_at": started_at,
        "status": status,
        "mode": "shadow_observation_and_execution",
        "chain": [
            "authoritative_universe",
            "market_data_v2",
            "signal_engine",
            "voting_engine",
            "risk_engine",
            "execution_plan_builder",
            "shadow_plan_adapter",
            "simulated_broker",
            "positions",
            "exposure",
            "idempotence",
        ],
        "funnel": {
            "risk_candidates": {
                "count": len(risk_rows),
                "symbols": risk_symbols,
            },
            "execution_candidate_orders": {
                "count": len(
                    candidate_orders
                ),
                "symbols": candidate_symbols,
            },
            "broker_orders": {
                "count": len(
                    executable_plan.get(
                        "orders",
                        [],
                    )
                ),
                "symbols": symbols_from_rows(
                    executable_plan.get(
                        "orders",
                        [],
                    )
                ),
            },
            "fills": {
                "count": len(fills),
                "symbols": symbols_from_rows(
                    fills
                ),
            },
            "positions": {
                "count": len(positions)
                if isinstance(
                    positions,
                    dict,
                )
                else 0,
                "symbols": sorted(
                    positions.keys()
                )
                if isinstance(
                    positions,
                    dict,
                )
                else [],
            },
        },
        "identity": {
            "source_plan_id": (
                execution_plan.get(
                    "plan_id"
                )
            ),
            "source_run_id": (
                execution_plan.get(
                    "run_id"
                )
            ),
            "broker_plan_id": (
                executable_plan.get(
                    "plan_id"
                )
            ),
            "broker_run_id": (
                executable_plan.get(
                    "run_id"
                )
            ),
        },
        "broker": {
            "fills_before": fills_before,
            "fills_after_run_1": (
                fills_after_run_1
            ),
            "fills_after_run_2": (
                fills_after_run_2
            ),
            "fills": fills,
            "rejections": rejections,
            "positions": positions,
            "exposure": exposure,
            "state": broker_state,
        },
        "tests": tests,
        "failed_tests": failed_tests,
        "canonical_integrity": {
            "verified_unchanged": (
                len(
                    changed_canonical_files
                )
                == 0
            ),
            "changed_files": (
                changed_canonical_files
            ),
            "before": canonical_before,
            "after": canonical_after,
        },
        "safety": {
            "real_broker_called": False,
            "real_execution_possible": False,
            "canonical_files_modified": bool(
                changed_canonical_files
            ),
            "shadow_only": True,
        },
        "commands": {
            "decision_chain": {
                "return_code": (
                    decision_result[
                        "return_code"
                    ]
                ),
                "stderr": (
                    decision_result[
                        "stderr"
                    ][-4000:]
                ),
            },
            "execution_plan": {
                "return_code": (
                    execution_result[
                        "return_code"
                    ]
                ),
                "stderr": (
                    execution_result[
                        "stderr"
                    ][-4000:]
                ),
            },
            "broker_run_1": {
                "return_code": (
                    broker_run_1[
                        "return_code"
                    ]
                ),
                "stderr": (
                    broker_run_1[
                        "stderr"
                    ][-4000:]
                ),
            },
            "broker_run_2": {
                "return_code": (
                    broker_run_2[
                        "return_code"
                    ]
                ),
                "stderr": (
                    broker_run_2[
                        "stderr"
                    ][-4000:]
                ),
            },
        },
        "blockers": blockers,
        "warnings": warnings,
        "output": str(OUTPUT),
    }

    write_json(
        OUTPUT,
        report,
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
