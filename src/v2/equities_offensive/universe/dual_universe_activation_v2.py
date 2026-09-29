from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.v2.equities_offensive.universe.run_dual_universe_builder_v2 import (
    DEFAULT_ROOT,
    build_universe_candidates,
    file_sha256,
    load_json,
    validate_governance_chain,
)


PROVIDER_LOCK = Path(
    "/run/lock/nsc-equities-provider-refresh.lock"
)

CANONICAL_LOCK = Path(
    "/run/lock/nsc-equities-offensive-canonical.lock"
)

ENGINE = "offensive_dual_universe_builder_v2"

CORE_UNIVERSE = "nasdaq_offensive_core"
TACTICAL_UNIVERSE = "nasdaq_offensive_tactical"


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )

    parser.add_argument(
        "--execute",
        action="store_true",
    )

    parser.add_argument(
        "--recover",
        action="store_true",
    )

    return parser.parse_args()


def artifact_paths(
    root: Path,
) -> dict[str, Path]:
    provider_root = (
        root / "market/providers"
    )

    universe_root = (
        root / "universe"
    )

    transaction_root = (
        universe_root
        / ".activation_v2"
    )

    return {
        "primary": (
            provider_root
            / "market_data_yfinance_v1.json"
        ),
        "secondary": (
            provider_root
            / "market_data_massive_v1.json"
        ),
        "validation": (
            provider_root
            / "cross_source_validation_v1.json"
        ),
        "gate": (
            provider_root
            / "provider_quality_gate_v1.json"
        ),
        "run_report": (
            provider_root
            / "provider_validation_run_v1.json"
        ),
        "shortlist": (
            universe_root
            / "shortlist_nasdaq.json"
        ),
        "active_core": (
            universe_root
            / "universe_filtered.json"
        ),
        "active_tactical": (
            universe_root
            / "tactical_watchlist.json"
        ),
        "transaction_root": (
            transaction_root
        ),
        "journal": (
            transaction_root
            / "journal.json"
        ),
        "backup_core": (
            transaction_root
            / "universe_filtered.before.json"
        ),
        "backup_tactical": (
            transaction_root
            / "tactical_watchlist.before.json"
        ),
    }


def atomic_write_bytes(
    path: Path,
    data: bytes,
    *,
    mode: int = 0o660,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    tmp = Path(tmp_name)

    try:
        with os.fdopen(
            fd,
            "wb",
        ) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            tmp,
            path,
        )

        os.chmod(
            path,
            mode,
        )

        directory_fd = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(
                directory_fd
            )
        finally:
            os.close(
                directory_fd
            )

    finally:
        tmp.unlink(
            missing_ok=True
        )


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    data = (
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    atomic_write_bytes(
        path,
        data,
    )


def sha256_bytes(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def fsync_directory(
    path: Path,
) -> None:
    fd = os.open(
        path,
        os.O_RDONLY,
    )

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate_provider_state(
    paths: dict[str, Path],
) -> dict[str, Any]:
    governance = validate_governance_chain(
        primary_path=paths["primary"],
        secondary_path=paths["secondary"],
        validation_path=paths["validation"],
        gate_path=paths["gate"],
        run_report_path=paths["run_report"],
    )

    primary = load_json(
        paths["primary"]
    )

    secondary = load_json(
        paths["secondary"]
    )

    primary_status = str(
        primary.get("status") or ""
    ).strip().lower()

    secondary_status = str(
        secondary.get("status") or ""
    ).strip().lower()

    if primary_status != "healthy":
        raise RuntimeError(
            "Primary provider is not healthy"
        )

    if secondary_status != "healthy":
        raise RuntimeError(
            "Secondary provider is not healthy"
        )

    primary_session = str(
        primary.get("market_session") or ""
    ).strip()

    secondary_session = str(
        secondary.get("market_session") or ""
    ).strip()

    if (
        not primary_session
        or primary_session
        != secondary_session
    ):
        raise RuntimeError(
            "Provider market_session mismatch"
        )

    primary_reference = str(
        primary.get("reference_time") or ""
    ).strip()

    secondary_reference = str(
        secondary.get("reference_time") or ""
    ).strip()

    if (
        not primary_reference
        or primary_reference
        != secondary_reference
    ):
        raise RuntimeError(
            "Provider reference_time mismatch"
        )

    return {
        "governance": governance,
        "primary": primary,
        "market_session": (
            primary_session
        ),
        "reference_time": (
            primary_reference
        ),
        "primary_sha256": file_sha256(
            paths["primary"]
        ),
        "secondary_sha256": file_sha256(
            paths["secondary"]
        ),
    }


def build_active_pair(
    paths: dict[str, Path],
    state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    shortlist = load_json(
        paths["shortlist"]
    )

    core, tactical = (
        build_universe_candidates(
            shortlist=shortlist,
            provider=state["primary"],
            governance=state[
                "governance"
            ],
            provider_path=paths["primary"],
            tactical_output=paths[
                "active_tactical"
            ],
            core_status="active_simulated",
            tactical_status="watch_only",
            schema_version="2.0",
            shadow_only=False,
        )
    )

    validate_active_pair(
        core,
        tactical,
    )

    return core, tactical


def validate_active_pair(
    core: dict[str, Any],
    tactical: dict[str, Any],
) -> None:
    for (
        name,
        doc,
        expected_universe,
        expected_status,
    ) in (
        (
            "core",
            core,
            CORE_UNIVERSE,
            "active_simulated",
        ),
        (
            "tactical",
            tactical,
            TACTICAL_UNIVERSE,
            "watch_only",
        ),
    ):
        if doc.get("engine") != ENGINE:
            raise RuntimeError(
                f"{name} engine mismatch"
            )

        if (
            doc.get("schema_version")
            != "2.0"
        ):
            raise RuntimeError(
                f"{name} schema mismatch"
            )

        if (
            doc.get("status")
            != expected_status
        ):
            raise RuntimeError(
                f"{name} status mismatch"
            )

        if (
            doc.get("universe")
            != expected_universe
        ):
            raise RuntimeError(
                f"{name} universe mismatch"
            )

        generation_id = str(
            doc.get("generation_id") or ""
        )

        if (
            len(generation_id) != 64
            or any(
                char
                not in "0123456789abcdef"
                for char in generation_id
            )
        ):
            raise RuntimeError(
                f"{name} generation_id invalid"
            )

        market_session = str(
            doc.get("market_session") or ""
        )

        if not market_session:
            raise RuntimeError(
                f"{name} market_session missing"
            )

        policy = doc.get(
            "execution_policy"
        )

        if not isinstance(
            policy,
            dict,
        ):
            raise RuntimeError(
                f"{name} execution_policy missing"
            )

        if (
            policy.get("shadow_only")
            is not False
        ):
            raise RuntimeError(
                f"{name} shadow_only not false"
            )

        if (
            policy.get(
                "direct_execution_allowed"
            )
            is not False
        ):
            raise RuntimeError(
                f"{name} direct execution "
                "must remain disabled"
            )

    tactical_policy = tactical[
        "execution_policy"
    ]

    for control in (
        "requires_tactical_risk_engine",
        "reduced_sizing_required",
        "sector_concentration_control_required",
        "enhanced_exit_protection_required",
    ):
        if (
            tactical_policy.get(control)
            is not True
        ):
            raise RuntimeError(
                "Tactical execution control "
                f"missing: {control}"
            )

    risk_limits = tactical.get(
        "risk_limits_pending"
    )

    if not isinstance(
        risk_limits,
        dict,
    ):
        raise RuntimeError(
            "Tactical risk_limits_pending missing"
        )

    expected_pending_limits = {
        "max_tactical_positions": None,
        "max_tactical_weight": None,
        "position_size_factor": None,
    }

    if (
        risk_limits
        != expected_pending_limits
    ):
        raise RuntimeError(
            "Unexpected tactical pending "
            "risk-limit contract"
        )

    if (
        core["generation_id"]
        != tactical["generation_id"]
    ):
        raise RuntimeError(
            "Universe generation mismatch"
        )

    if (
        core["market_session"]
        != tactical["market_session"]
    ):
        raise RuntimeError(
            "Universe market_session mismatch"
        )

    if (
        set(core.get("symbols") or [])
        & set(tactical.get("symbols") or [])
    ):
        raise RuntimeError(
            "Core/Tactical overlap"
        )


def candidate_report(
    core: dict[str, Any],
    tactical: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "candidate_ready",
        "mode": "dry_run",
        "activation_executed": False,
        "active_files_modified": False,
        "market_session": (
            core["market_session"]
        ),
        "generation_id": (
            core["generation_id"]
        ),
        "reference_time": (
            state["reference_time"]
        ),
        "core_symbols": (
            core["symbols"]
        ),
        "tactical_symbols": (
            tactical["symbols"]
        ),
        "primary_sha256": (
            state["primary_sha256"]
        ),
        "secondary_sha256": (
            state["secondary_sha256"]
        ),
    }


def recover_transaction(
    paths: dict[str, Path],
) -> dict[str, Any]:
    journal_path = paths["journal"]

    if not journal_path.exists():
        return {
            "status": "no_recovery_needed",
            "recovered": False,
        }

    journal = load_json(
        journal_path
    )

    state = str(
        journal.get("state") or ""
    )

    if state == "committed":
        return {
            "status": "already_committed",
            "recovered": False,
        }

    core_backup = paths[
        "backup_core"
    ]
    tactical_backup = paths[
        "backup_tactical"
    ]

    if (
        not core_backup.is_file()
        or not tactical_backup.is_file()
    ):
        raise RuntimeError(
            "Recovery backups missing"
        )

    core_before = (
        core_backup.read_bytes()
    )
    tactical_before = (
        tactical_backup.read_bytes()
    )

    expected_core_sha = str(
        journal.get(
            "core_before_sha256"
        )
        or ""
    )

    expected_tactical_sha = str(
        journal.get(
            "tactical_before_sha256"
        )
        or ""
    )

    if (
        sha256_bytes(core_before)
        != expected_core_sha
    ):
        raise RuntimeError(
            "Core recovery backup SHA mismatch"
        )

    if (
        sha256_bytes(tactical_before)
        != expected_tactical_sha
    ):
        raise RuntimeError(
            "Tactical recovery backup SHA mismatch"
        )

    atomic_write_bytes(
        paths["active_core"],
        core_before,
    )

    atomic_write_bytes(
        paths["active_tactical"],
        tactical_before,
    )

    journal["state"] = "recovered"
    journal["recovered_at"] = (
        utc_now_iso()
    )

    atomic_write_json(
        journal_path,
        journal,
    )

    return {
        "status": "recovered",
        "recovered": True,
    }


def durable_activate_pair(
    paths: dict[str, Path],
    core: dict[str, Any],
    tactical: dict[str, Any],
) -> dict[str, Any]:
    validate_active_pair(
        core,
        tactical,
    )

    if paths["journal"].exists():
        existing = load_json(
            paths["journal"]
        )

        if (
            existing.get("state")
            not in (
                "committed",
                "recovered",
            )
        ):
            raise RuntimeError(
                "Unresolved activation journal"
            )

    core_before = (
        paths["active_core"]
        .read_bytes()
    )

    tactical_before = (
        paths["active_tactical"]
        .read_bytes()
    )

    transaction_root = paths[
        "transaction_root"
    ]

    transaction_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_bytes(
        paths["backup_core"],
        core_before,
    )

    atomic_write_bytes(
        paths["backup_tactical"],
        tactical_before,
    )

    journal = {
        "schema_version": "1.0",
        "transaction": (
            "universe_v2_activation"
        ),
        "state": "prepared",
        "prepared_at": utc_now_iso(),
        "core_target": str(
            paths["active_core"]
        ),
        "tactical_target": str(
            paths["active_tactical"]
        ),
        "core_before_sha256": (
            sha256_bytes(
                core_before
            )
        ),
        "tactical_before_sha256": (
            sha256_bytes(
                tactical_before
            )
        ),
        "generation_id": (
            core["generation_id"]
        ),
        "market_session": (
            core["market_session"]
        ),
    }

    atomic_write_json(
        paths["journal"],
        journal,
    )

    try:
        atomic_write_json(
            paths["active_core"],
            core,
        )

        journal["state"] = (
            "core_written"
        )

        atomic_write_json(
            paths["journal"],
            journal,
        )

        atomic_write_json(
            paths["active_tactical"],
            tactical,
        )

        journal["state"] = (
            "pair_written"
        )

        atomic_write_json(
            paths["journal"],
            journal,
        )

        written_core = load_json(
            paths["active_core"]
        )

        written_tactical = load_json(
            paths["active_tactical"]
        )

        validate_active_pair(
            written_core,
            written_tactical,
        )

        if (
            written_core["generation_id"]
            != core["generation_id"]
        ):
            raise RuntimeError(
                "Written core generation mismatch"
            )

        journal["state"] = "committed"
        journal["committed_at"] = (
            utc_now_iso()
        )

        journal[
            "core_after_sha256"
        ] = file_sha256(
            paths["active_core"]
        )

        journal[
            "tactical_after_sha256"
        ] = file_sha256(
            paths["active_tactical"]
        )

        atomic_write_json(
            paths["journal"],
            journal,
        )

        fsync_directory(
            transaction_root
        )

        return {
            "status": "activated",
            "activation_executed": True,
            "market_session": (
                core["market_session"]
            ),
            "generation_id": (
                core["generation_id"]
            ),
            "core_sha256": (
                journal[
                    "core_after_sha256"
                ]
            ),
            "tactical_sha256": (
                journal[
                    "tactical_after_sha256"
                ]
            ),
        }

    except BaseException:
        atomic_write_bytes(
            paths["active_core"],
            core_before,
        )

        atomic_write_bytes(
            paths["active_tactical"],
            tactical_before,
        )

        journal["state"] = (
            "rolled_back"
        )

        journal["rolled_back_at"] = (
            utc_now_iso()
        )

        atomic_write_json(
            paths["journal"],
            journal,
        )

        raise


def locked_candidate(
    paths: dict[str, Path],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    state = validate_provider_state(
        paths
    )

    core, tactical = build_active_pair(
        paths,
        state,
    )

    return state, core, tactical


def main() -> int:
    args = parse_args()

    if args.execute:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "mode": "execute",
                    "activation_executed": False,
                    "active_files_modified": False,
                    "reason": "standalone_universe_execute_disabled_use_global_four_artifact_cutover",
                    "required_authority": (
                        "four_artifact_cutover_v2"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 3

    if args.recover:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "mode": "recover",
                    "recovery_executed": False,
                    "active_files_modified": False,
                    "reason": "standalone_universe_recover_disabled_use_global_four_artifact_cutover",
                    "required_authority": (
                        "four_artifact_cutover_v2"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 3

    paths = artifact_paths(
        args.root
    )

    PROVIDER_LOCK.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if args.execute:
        #
        # Lock ordering is deliberate:
        #
        #   provider SH -> canonical EX
        #
        # Provider state therefore cannot change
        # while we wait for or hold the canonical
        # activation lock.
        #
        # Governance and candidate construction are
        # performed only after BOTH locks are held.
        #
        with PROVIDER_LOCK.open(
            "r"
        ) as provider_lock:
            fcntl.flock(
                provider_lock.fileno(),
                fcntl.LOCK_SH,
            )

            try:
                with CANONICAL_LOCK.open(
                    "a+"
                ) as canonical_lock:
                    fcntl.flock(
                        canonical_lock.fileno(),
                        fcntl.LOCK_EX,
                    )

                    try:
                        try:
                            state, core, tactical = (
                                locked_candidate(
                                    paths
                                )
                            )

                            if (
                                core["market_session"]
                                != state["market_session"]
                            ):
                                raise RuntimeError(
                                    "Candidate/provider "
                                    "market_session mismatch"
                                )

                            report = (
                                durable_activate_pair(
                                    paths,
                                    core,
                                    tactical,
                                )
                            )

                            report[
                                "reference_time"
                            ] = state[
                                "reference_time"
                            ]

                            report[
                                "primary_sha256"
                            ] = state[
                                "primary_sha256"
                            ]

                            report[
                                "secondary_sha256"
                            ] = state[
                                "secondary_sha256"
                            ]

                        except Exception as exc:
                            print(
                                json.dumps(
                                    {
                                        "status": "blocked",
                                        "mode": "execute",
                                        "activation_executed": False,
                                        "reason": str(exc),
                                    },
                                    indent=2,
                                    sort_keys=True,
                                )
                            )

                            return 2

                    finally:
                        fcntl.flock(
                            canonical_lock.fileno(),
                            fcntl.LOCK_UN,
                        )

            finally:
                fcntl.flock(
                    provider_lock.fileno(),
                    fcntl.LOCK_UN,
                )

        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    #
    # Dry-run takes the provider shared lock,
    # validates the complete governance chain,
    # and builds the exact active candidate.
    #
    with PROVIDER_LOCK.open(
        "r"
    ) as provider_lock:
        fcntl.flock(
            provider_lock.fileno(),
            fcntl.LOCK_SH,
        )

        try:
            try:
                state, core, tactical = (
                    locked_candidate(
                        paths
                    )
                )
            except Exception as exc:
                print(
                    json.dumps(
                        {
                            "status": "blocked",
                            "mode": "dry_run",
                            "activation_executed": False,
                            "active_files_modified": False,
                            "reason": str(exc),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )

                return 2

        finally:
            fcntl.flock(
                provider_lock.fileno(),
                fcntl.LOCK_UN,
            )

    print(
        json.dumps(
            candidate_report(
                core,
                tactical,
                state,
            ),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
