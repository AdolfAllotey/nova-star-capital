#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Shadow Simulated Broker Runner V1

Objectifs :
- exécuter le Simulated Broker existant dans un environnement isolé ;
- rediriger toutes ses lectures et écritures vers shadow_v2/broker_v1 ;
- ne jamais modifier les artefacts canoniques ;
- ne jamais exécuter d'ordre réel.

Le module canonique simulated_broker.py n'est pas modifié.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_ROOT = Path("/opt/nsc/app")

CANONICAL_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

SHADOW_ROOT = (
    CANONICAL_ROOT
    / "shadow_v2/broker_v1"
)

BROKER_SOURCE = (
    APP_ROOT
    / "src/v2/equities_offensive/broker/"
    "simulated_broker.py"
)

DEFAULT_PLAN = (
    SHADOW_ROOT
    / "execution/execution_plan.json"
)

DEFAULT_FILLS = (
    SHADOW_ROOT
    / "execution/simulated_fills.jsonl"
)

DEFAULT_REJECTED = (
    SHADOW_ROOT
    / "execution/rejected_orders.jsonl"
)

DEFAULT_POSITIONS = (
    SHADOW_ROOT
    / "state/positions.json"
)

DEFAULT_EXPOSURE = (
    SHADOW_ROOT
    / "state/exposure_snapshot.json"
)

DEFAULT_STATE = (
    SHADOW_ROOT
    / "state/state.json"
)

DEFAULT_LOCK = (
    SHADOW_ROOT
    / "state/state.lock"
)

DEFAULT_PRICES = (
    CANONICAL_ROOT
    / "market/providers/staging/"
    "prices.candidate.json"
)

DEFAULT_REPORT = (
    SHADOW_ROOT
    / "reports/shadow_simulated_broker_run_v1.json"
)

CANONICAL_FILES = [
    CANONICAL_ROOT
    / "execution/execution_plan.json",
    CANONICAL_ROOT
    / "execution/simulated_fills.jsonl",
    CANONICAL_ROOT
    / "execution/rejected_orders.jsonl",
    CANONICAL_ROOT
    / "state/positions.json",
    CANONICAL_ROOT
    / "state/state.json",
    CANONICAL_ROOT
    / "state/exposure_snapshot.json",
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


def file_sha256(
    path: Path,
) -> str | None:
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


def capture_hashes(
    paths: list[Path],
) -> dict[str, str | None]:
    return {
        str(path): file_sha256(path)
        for path in paths
    }


def jsonl_rows(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        if not line.strip():
            continue

        try:
            row = json.loads(line)

            if isinstance(row, dict):
                rows.append(row)
        except Exception:
            continue

    return rows


def load_isolated_broker(
    *,
    plan_path: Path,
    fills_path: Path,
    rejected_path: Path,
    positions_path: Path,
    exposure_path: Path,
    prices_path: Path,
    state_path: Path,
    lock_path: Path,
) -> types.ModuleType:
    if not BROKER_SOURCE.exists():
        raise FileNotFoundError(
            f"Broker source absent : {BROKER_SOURCE}"
        )

    source = BROKER_SOURCE.read_text(
        encoding="utf-8",
    )

    canonical_rejected = (
        "/opt/nsc/data/preprod/"
        "equities_offensive/execution/"
        "rejected_orders.jsonl"
    )

    source = source.replace(
        canonical_rejected,
        str(rejected_path),
    )

    module_name = (
        "nsc_shadow_simulated_broker_runtime"
    )

    module = types.ModuleType(module_name)

    module.__file__ = str(BROKER_SOURCE)
    module.__package__ = (
        "src.v2.equities_offensive.broker"
    )

    sys.modules[module_name] = module

    compiled = compile(
        source,
        str(BROKER_SOURCE),
        "exec",
    )

    exec(
        compiled,
        module.__dict__,
    )

    module.ROOT = SHADOW_ROOT
    module.PLAN_PATH = plan_path
    module.FILLS_PATH = fills_path
    module.POSITIONS_PATH = positions_path
    module.EXPOSURE_PATH = exposure_path
    module.PRICES_PATH = prices_path

    original_state_store = module.StateStore

    def shadow_state_store_factory(
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        kwargs["state_path"] = state_path
        kwargs["lock_path"] = lock_path

        return original_state_store(
            *args,
            **kwargs,
        )

    module.StateStore = shadow_state_store_factory

    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exécute le Simulated Broker "
            "dans un espace Shadow isolé."
        )
    )

    parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN,
    )

    parser.add_argument(
        "--fills",
        type=Path,
        default=DEFAULT_FILLS,
    )

    parser.add_argument(
        "--rejected",
        type=Path,
        default=DEFAULT_REJECTED,
    )

    parser.add_argument(
        "--positions",
        type=Path,
        default=DEFAULT_POSITIONS,
    )

    parser.add_argument(
        "--exposure",
        type=Path,
        default=DEFAULT_EXPOSURE,
    )

    parser.add_argument(
        "--prices",
        type=Path,
        default=DEFAULT_PRICES,
    )

    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE,
    )

    parser.add_argument(
        "--lock",
        type=Path,
        default=DEFAULT_LOCK,
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    for path in (
        args.plan,
        args.fills,
        args.rejected,
        args.positions,
        args.exposure,
        args.state,
        args.lock,
        args.report,
    ):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    canonical_before = capture_hashes(
        CANONICAL_FILES
    )

    fills_before = jsonl_rows(
        args.fills
    )

    rejected_before = jsonl_rows(
        args.rejected
    )

    exception_message: str | None = None

    try:
        module = load_isolated_broker(
            plan_path=args.plan,
            fills_path=args.fills,
            rejected_path=args.rejected,
            positions_path=args.positions,
            exposure_path=args.exposure,
            prices_path=args.prices,
            state_path=args.state,
            lock_path=args.lock,
        )

        module.main()

    except Exception as exc:
        exception_message = (
            f"{type(exc).__name__}: {exc}"
        )

    canonical_after = capture_hashes(
        CANONICAL_FILES
    )

    changed_files = [
        path
        for path in canonical_before
        if (
            canonical_before.get(path)
            != canonical_after.get(path)
        )
    ]

    fills_after = jsonl_rows(
        args.fills
    )

    rejected_after = jsonl_rows(
        args.rejected
    )

    plan = read_json(
        args.plan,
        {},
    ) or {}

    state = read_json(
        args.state,
        {},
    ) or {}

    positions = read_json(
        args.positions,
        {},
    ) or {}

    exposure = read_json(
        args.exposure,
        {},
    ) or {}

    blockers: list[str] = []

    if exception_message:
        blockers.append(
            exception_message
        )

    if changed_files:
        blockers.append(
            "Un ou plusieurs fichiers "
            "canoniques ont été modifiés."
        )

    status = (
        "shadow_broker_completed"
        if not blockers
        else "shadow_broker_failed"
    )

    report = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_equities_"
            "shadow_simulated_broker_run"
        ),
        "generated_at": utc_now_iso(),
        "status": status,
        "mode": "shadow_simulated_only",
        "canonical_files_modified": bool(
            changed_files
        ),
        "canonical_integrity": {
            "verified_unchanged": (
                not changed_files
            ),
            "changed_files": changed_files,
        },
        "broker_source_modified": False,
        "real_execution_possible": False,
        "inputs": {
            "plan": str(args.plan),
            "prices": str(args.prices),
        },
        "outputs": {
            "fills": str(args.fills),
            "rejected": str(args.rejected),
            "positions": str(args.positions),
            "exposure": str(args.exposure),
            "state": str(args.state),
        },
        "plan": {
            "plan_id": plan.get("plan_id"),
            "run_id": plan.get("run_id"),
            "action_policy": (
                plan.get("action_policy")
            ),
            "orders_count": len(
                plan.get("orders") or []
            ),
        },
        "result": {
            "fills_before": len(
                fills_before
            ),
            "fills_after": len(
                fills_after
            ),
            "fills_created": (
                len(fills_after)
                - len(fills_before)
            ),
            "rejections_before": len(
                rejected_before
            ),
            "rejections_after": len(
                rejected_after
            ),
            "rejections_created": (
                len(rejected_after)
                - len(rejected_before)
            ),
            "position_symbols": sorted(
                positions.keys()
            )
            if isinstance(
                positions,
                dict,
            )
            else [],
            "orders_seen": (
                state.get("orders_seen")
                if isinstance(state, dict)
                else []
            ),
            "orders_seen_plan_id": (
                state.get(
                    "orders_seen_plan_id"
                )
                if isinstance(state, dict)
                else None
            ),
            "last_broker_run": (
                state.get(
                    "last_broker_run"
                )
                if isinstance(state, dict)
                else None
            ),
            "exposure": exposure,
        },
        "exception": exception_message,
        "blockers": blockers,
    }

    atomic_write_json(
        args.report,
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
    raise SystemExit(main())
