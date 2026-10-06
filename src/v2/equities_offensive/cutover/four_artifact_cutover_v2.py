from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import tempfile
import sys
from pathlib import Path
from typing import Any

from src.v2.equities_offensive.market.providers import (
    provider_canonical_promotion_v2 as market_authority,
)
from src.v2.equities_offensive.universe import (
    dual_universe_activation_v2 as universe_authority,
)


DEFAULT_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

PROVIDER_LOCK = Path(
    "/run/lock/nsc-equities-provider-refresh.lock"
)

CANONICAL_LOCK = Path(
    "/run/lock/nsc-equities-offensive-canonical.lock"
)

MARKET_ENGINE = (
    "offensive_canonical_market_feed_v2"
)

SNAPSHOT_ENGINE = (
    "offensive_canonical_snapshot_v2"
)

UNIVERSE_ENGINE = (
    "offensive_dual_universe_builder_v2"
)

CORE_UNIVERSE = "nasdaq_offensive_core"
TACTICAL_UNIVERSE = (
    "nasdaq_offensive_tactical"
)

EXPECTED_PENDING_LIMITS = {
    "max_tactical_positions": None,
    "max_tactical_weight": None,
    "position_size_factor": None,
}

TACTICAL_CONTROLS = (
    "requires_tactical_risk_engine",
    "reduced_sizing_required",
    "sector_concentration_control_required",
    "enhanced_exit_protection_required",
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
        "--authorization-digest",
        type=str,
        default=None,
        help=(
            "Exact SHA256 authorization digest emitted "
            "by a prior dry-run candidate."
        ),
    )

    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def artifact_paths(
    root: Path,
) -> dict[str, Path]:
    provider_root = (
        root / "market/providers"
    )

    universe_root = (
        root / "universe"
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
        "prices": (
            root / "market/prices.json"
        ),
        "snapshot": (
            universe_root
            / "price_snapshot.json"
        ),
        "core": (
            universe_root
            / "universe_filtered.json"
        ),
        "tactical": (
            universe_root
            / "tactical_watchlist.json"
        ),
    }


def valid_generation_id(
    value: Any,
) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(
            char in "0123456789abcdef"
            for char in value
        )
    )


def validate_runtime_contract(
    prices: dict[str, Any],
    snapshot: dict[str, Any],
    core: dict[str, Any],
    tactical: dict[str, Any],
) -> None:
    if (
        prices.get("engine")
        != MARKET_ENGINE
    ):
        raise RuntimeError(
            "prices_engine_not_v2"
        )

    if (
        snapshot.get("engine")
        != SNAPSHOT_ENGINE
    ):
        raise RuntimeError(
            "snapshot_engine_not_v2"
        )

    for name, doc in (
        ("prices", prices),
        ("snapshot", snapshot),
    ):
        if doc.get("canonical") is not True:
            raise RuntimeError(
                f"{name}_not_canonical"
            )

        if (
            doc.get("status")
            != "active_simulated"
        ):
            raise RuntimeError(
                f"{name}_status_invalid"
            )

        if not valid_generation_id(
            doc.get("generation_id")
        ):
            raise RuntimeError(
                f"{name}_generation_id_invalid"
            )

        if not str(
            doc.get("market_session") or ""
        ).strip():
            raise RuntimeError(
                f"{name}_market_session_missing"
            )

    if (
        prices["generation_id"]
        != snapshot["generation_id"]
    ):
        raise RuntimeError(
            "market_generation_mismatch"
        )

    if (
        set(prices.get("prices") or {})
        != set(snapshot.get("prices") or {})
    ):
        raise RuntimeError(
            "market_symbol_set_mismatch"
        )

    expected_universe = {
        "core": (
            CORE_UNIVERSE,
            "active_simulated",
            "core",
        ),
        "tactical": (
            TACTICAL_UNIVERSE,
            "watch_only",
            "tactical_high_volatility",
        ),
    }

    for name, doc in (
        ("core", core),
        ("tactical", tactical),
    ):
        (
            universe,
            status,
            role,
        ) = expected_universe[name]

        if (
            doc.get("engine")
            != UNIVERSE_ENGINE
        ):
            raise RuntimeError(
                f"{name}_engine_not_v2"
            )

        if (
            doc.get("schema_version")
            != "2.0"
        ):
            raise RuntimeError(
                f"{name}_schema_invalid"
            )

        if (
            doc.get("universe")
            != universe
        ):
            raise RuntimeError(
                f"{name}_universe_invalid"
            )

        if doc.get("status") != status:
            raise RuntimeError(
                f"{name}_status_invalid"
            )

        if (
            doc.get("universe_role")
            != role
        ):
            raise RuntimeError(
                f"{name}_role_invalid"
            )

        if not valid_generation_id(
            doc.get("generation_id")
        ):
            raise RuntimeError(
                f"{name}_generation_id_invalid"
            )

        if not str(
            doc.get("market_session") or ""
        ).strip():
            raise RuntimeError(
                f"{name}_market_session_missing"
            )

        policy = doc.get(
            "execution_policy"
        )

        if not isinstance(policy, dict):
            raise RuntimeError(
                f"{name}_execution_policy_missing"
            )

        if (
            policy.get("shadow_only")
            is not False
        ):
            raise RuntimeError(
                f"{name}_shadow_only_not_false"
            )

        if (
            policy.get(
                "direct_execution_allowed"
            )
            is not False
        ):
            raise RuntimeError(
                f"{name}_direct_execution_not_false"
            )

    tactical_policy = tactical[
        "execution_policy"
    ]

    for control in TACTICAL_CONTROLS:
        if (
            tactical_policy.get(control)
            is not True
        ):
            raise RuntimeError(
                "tactical_control_invalid:"
                f"{control}"
            )

    if (
        tactical.get("risk_limits_pending")
        != EXPECTED_PENDING_LIMITS
    ):
        raise RuntimeError(
            "tactical_pending_limits_invalid"
        )

    if (
        core["generation_id"]
        != tactical["generation_id"]
    ):
        raise RuntimeError(
            "universe_generation_mismatch"
        )

    if (
        set(core.get("symbols") or [])
        & set(tactical.get("symbols") or [])
    ):
        raise RuntimeError(
            "core_tactical_overlap"
        )

    sessions = {
        str(
            prices.get("market_session")
            or ""
        ),
        str(
            snapshot.get("market_session")
            or ""
        ),
        str(
            core.get("market_session")
            or ""
        ),
        str(
            tactical.get("market_session")
            or ""
        ),
    }

    if "" in sessions:
        raise RuntimeError(
            "four_artifact_session_missing"
        )

    if len(sessions) != 1:
        raise RuntimeError(
            "four_artifact_session_mismatch"
        )


def build_locked_candidate(
    paths: dict[str, Path],
) -> dict[str, Any]:
    universe_paths = (
        universe_authority.artifact_paths(
            paths["prices"].parents[1]
        )
    )

    state = (
        universe_authority
        .validate_provider_state(
            universe_paths
        )
    )

    primary = state["primary"]

    validation = (
        market_authority.read_json(
            paths["validation"]
        )
    )

    gate = (
        market_authority.read_json(
            paths["gate"]
        )
    )

    market_validation = (
        market_authority.validate_inputs(
            primary,
            validation,
            gate,
        )
    )

    blockers = (
        market_validation["blockers"]
    )

    if blockers:
        raise RuntimeError(
            "market_validation_blocked:"
            + ",".join(
                str(item)
                for item in blockers
            )
        )

    market_session = str(
        market_validation.get(
            "market_session"
        )
        or ""
    )

    if not market_session:
        raise RuntimeError(
            "market_session_missing"
        )

    if (
        market_session
        != state["market_session"]
    ):
        raise RuntimeError(
            "market_universe_provider_session_mismatch"
        )

    (
        prices,
        snapshot,
    ) = (
        market_authority
        .build_canonical_artifacts(
            primary,
            validation,
        )
    )

    core, tactical = (
        universe_authority
        .build_active_pair(
            universe_paths,
            state,
        )
    )

    market_authority.verify_written_contract
    universe_authority.validate_active_pair(
        core,
        tactical,
    )

    validate_runtime_contract(
        prices,
        snapshot,
        core,
        tactical,
    )

    return {
        "provider": {
            "market_session": (
                state["market_session"]
            ),
            "reference_time": (
                state["reference_time"]
            ),
            "primary_sha256": (
                state["primary_sha256"]
            ),
            "secondary_sha256": (
                state["secondary_sha256"]
            ),
            "validation_sha256": (
                sha256_file(
                    paths["validation"]
                )
            ),
            "gate_sha256": (
                sha256_file(
                    paths["gate"]
                )
            ),
            "run_report_sha256": (
                sha256_file(
                    paths["run_report"]
                )
            ),
        },
        "market": {
            "generation_id": (
                prices["generation_id"]
            ),
            "market_session": (
                prices["market_session"]
            ),
            "symbol_count": len(
                prices["prices"]
            ),
            "prices_engine": (
                prices["engine"]
            ),
            "snapshot_engine": (
                snapshot["engine"]
            ),
        },
        "universe": {
            "generation_id": (
                core["generation_id"]
            ),
            "market_session": (
                core["market_session"]
            ),
            "core_status": (
                core["status"]
            ),
            "tactical_status": (
                tactical["status"]
            ),
            "core_symbols": (
                core.get("symbols") or []
            ),
            "tactical_symbols": (
                tactical.get("symbols")
                or []
            ),
        },
        "candidate_payloads": {
            "prices": prices,
            "snapshot": snapshot,
            "core": core,
            "tactical": tactical,
        },
    }


def candidate_authorization_hashes(
    candidate: dict[str, Any],
) -> dict[str, str]:
    payloads = candidate[
        "candidate_payloads"
    ]

    candidate_bytes = (
        candidate_artifact_bytes(
            prices=payloads["prices"],
            snapshot=payloads["snapshot"],
            core=payloads["core"],
            tactical=payloads["tactical"],
        )
    )

    return hash_artifact_bytes(
        candidate_bytes
    )


def authorization_payload(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    provider = candidate["provider"]
    market = candidate["market"]
    universe = candidate["universe"]

    candidate_hashes = (
        candidate_authorization_hashes(
            candidate
        )
    )

    return {
        "market_session": (
            provider["market_session"]
        ),
        "reference_time": (
            provider["reference_time"]
        ),
        "primary_sha256": (
            provider["primary_sha256"]
        ),
        "secondary_sha256": (
            provider["secondary_sha256"]
        ),
        "validation_sha256": (
            provider["validation_sha256"]
        ),
        "gate_sha256": (
            provider["gate_sha256"]
        ),
        "run_report_sha256": (
            provider["run_report_sha256"]
        ),
        "market_generation_id": (
            market["generation_id"]
        ),
        "universe_generation_id": (
            universe["generation_id"]
        ),
        "prices_candidate_sha256": (
            candidate_hashes["prices"]
        ),
        "snapshot_candidate_sha256": (
            candidate_hashes["snapshot"]
        ),
        "core_candidate_sha256": (
            candidate_hashes["core"]
        ),
        "tactical_candidate_sha256": (
            candidate_hashes["tactical"]
        ),
        "core_symbols": (
            universe["core_symbols"]
        ),
        "tactical_symbols": (
            universe["tactical_symbols"]
        ),
    }


def authorization_digest(
    candidate: dict[str, Any],
) -> str:
    payload = authorization_payload(
        candidate
    )

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def validate_authorization_digest(
    candidate: dict[str, Any],
    supplied: str | None,
) -> str:
    expected = authorization_digest(
        candidate
    )

    supplied_value = str(
        supplied or ""
    ).strip().lower()

    if not supplied_value:
        raise RuntimeError(
            "cutover_authorization_digest_missing"
        )

    if supplied_value != expected:
        raise RuntimeError(
            "cutover_authorization_digest_mismatch"
        )

    return expected


def public_report(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_four_artifact_cutover"
        ),
        "status": "candidate_ready",
        "mode": "dry_run",
        "cutover_executed": False,
        "active_files_modified": False,
        "authorization": {
            "digest_algorithm": "sha256",
            "digest": authorization_digest(
                candidate
            ),
            "payload": authorization_payload(
                candidate
            ),
        },
        "lock_order": [
            "provider_shared",
            "canonical_exclusive",
        ],
        "provider": candidate["provider"],
        "market": candidate["market"],
        "universe": candidate["universe"],
        "global_contract": {
            "single_provider_snapshot": True,
            "four_artifact_session_equal": True,
            "market_generation_internal": True,
            "universe_generation_internal": True,
            "market_universe_generation_equality_required": False,
            "global_transaction_required_for_execute": True,
            "global_rollback_required": True,
            "global_crash_recovery_required": True,
        },
    }



GLOBAL_TRANSACTION_SCHEMA = "1.0"

GLOBAL_TRANSACTION_TYPE = (
    "offensive_four_artifact_cutover_v2"
)

GLOBAL_TRANSACTION_DIRNAME = (
    ".four_artifact_cutover_v2"
)

GLOBAL_ARTIFACT_NAMES = (
    "prices",
    "snapshot",
    "core",
    "tactical",
)


def sha256_bytes(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def fsync_directory(
    directory: Path,
) -> None:
    fd = os.open(
        directory,
        os.O_RDONLY
        | getattr(
            os,
            "O_DIRECTORY",
            0,
        ),
    )

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_bytes(
    path: Path,
    data: bytes,
    *,
    mode: int | None = None,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing_mode: int | None = None
    existing_uid: int | None = None
    existing_gid: int | None = None

    if path.exists():
        existing_stat = path.stat()

        existing_mode = (
            existing_stat.st_mode
            & 0o7777
        )

        existing_uid = (
            existing_stat.st_uid
        )

        existing_gid = (
            existing_stat.st_gid
        )

    fd, temporary_raw = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
    )

    temporary = Path(
        temporary_raw
    )

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

        final_mode = (
            mode
            if mode is not None
            else existing_mode
        )

        if (
            existing_uid is not None
            and existing_gid is not None
        ):
            os.chown(
                temporary,
                existing_uid,
                existing_gid,
            )

        if final_mode is not None:
            os.chmod(
                temporary,
                final_mode,
            )

        os.replace(
            temporary,
            path,
        )

        fsync_directory(
            path.parent
        )

    finally:
        temporary.unlink(
            missing_ok=True
        )


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    encoded = (
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
        encoded,
        mode=0o660,
    )


def global_transaction_paths(
    root: Path,
) -> dict[str, Path]:
    transaction_root = (
        root
        / GLOBAL_TRANSACTION_DIRNAME
    )

    return {
        "transaction_root": (
            transaction_root
        ),
        "journal": (
            transaction_root
            / "journal.json"
        ),
        "backup_prices": (
            transaction_root
            / "prices.before.json"
        ),
        "backup_snapshot": (
            transaction_root
            / "price_snapshot.before.json"
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


def active_artifact_paths(
    root: Path,
) -> dict[str, Path]:
    return {
        "prices": (
            root
            / "market"
            / "prices.json"
        ),
        "snapshot": (
            root
            / "universe"
            / "price_snapshot.json"
        ),
        "core": (
            root
            / "universe"
            / "universe_filtered.json"
        ),
        "tactical": (
            root
            / "universe"
            / "tactical_watchlist.json"
        ),
    }


def candidate_artifact_bytes(
    *,
    prices: dict[str, Any],
    snapshot: dict[str, Any],
    core: dict[str, Any],
    tactical: dict[str, Any],
) -> dict[str, bytes]:
    payloads = {
        "prices": prices,
        "snapshot": snapshot,
        "core": core,
        "tactical": tactical,
    }

    return {
        name: (
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        for name, payload
        in payloads.items()
    }


def read_active_bytes(
    active: dict[str, Path],
) -> dict[str, bytes]:
    result: dict[str, bytes] = {}

    for name in GLOBAL_ARTIFACT_NAMES:
        path = active[name]

        if not path.is_file():
            raise RuntimeError(
                "global_active_artifact_missing:"
                f"{name}:{path}"
            )

        result[name] = (
            path.read_bytes()
        )

    return result


def hash_artifact_bytes(
    payloads: dict[str, bytes],
) -> dict[str, str]:
    return {
        name: sha256_bytes(
            payloads[name]
        )
        for name in GLOBAL_ARTIFACT_NAMES
    }


def validate_global_candidate(
    *,
    prices: dict[str, Any],
    snapshot: dict[str, Any],
    core: dict[str, Any],
    tactical: dict[str, Any],
) -> None:
    # Reuse the already-certified local authorities.
    market_session = str(
        prices.get(
            "market_session"
        )
        or ""
    )

    if not market_session:
        raise RuntimeError(
            "global_market_session_missing"
        )

    market_authority.verify_written_contract_payloads(
        prices,
        snapshot,
        market_session,
    ) if hasattr(
        market_authority,
        "verify_written_contract_payloads",
    ) else None

    # Explicit in-memory market contract because the
    # existing market verifier is path-based.
    if (
        prices.get("canonical")
        is not True
    ):
        raise RuntimeError(
            "global_prices_not_canonical"
        )

    if (
        snapshot.get("canonical")
        is not True
    ):
        raise RuntimeError(
            "global_snapshot_not_canonical"
        )

    if (
        prices.get("engine")
        != MARKET_ENGINE
    ):
        raise RuntimeError(
            "global_prices_engine_mismatch"
        )

    if (
        snapshot.get("engine")
        != SNAPSHOT_ENGINE
    ):
        raise RuntimeError(
            "global_snapshot_engine_mismatch"
        )

    prices_generation = str(
        prices.get(
            "generation_id"
        )
        or ""
    )

    snapshot_generation = str(
        snapshot.get(
            "generation_id"
        )
        or ""
    )

    if (
        len(prices_generation) != 64
        or any(
            char
            not in "0123456789abcdef"
            for char in prices_generation
        )
    ):
        raise RuntimeError(
            "global_prices_generation_invalid"
        )

    if (
        prices_generation
        != snapshot_generation
    ):
        raise RuntimeError(
            "global_market_generation_mismatch"
        )

    if (
        snapshot.get(
            "market_session"
        )
        != market_session
    ):
        raise RuntimeError(
            "global_market_session_mismatch"
        )

    price_rows = prices.get(
        "prices"
    )

    snapshot_rows = snapshot.get(
        "prices"
    )

    if (
        not isinstance(
            price_rows,
            dict,
        )
        or not isinstance(
            snapshot_rows,
            dict,
        )
        or not price_rows
        or set(price_rows)
        != set(snapshot_rows)
    ):
        raise RuntimeError(
            "global_market_symbol_contract_invalid"
        )

    universe_authority.validate_active_pair(
        core,
        tactical,
    )

    if (
        core.get("market_session")
        != market_session
        or tactical.get(
            "market_session"
        )
        != market_session
    ):
        raise RuntimeError(
            "global_four_artifact_session_mismatch"
        )


def restore_global_before(
    *,
    active: dict[str, Path],
    before: dict[str, bytes],
) -> None:
    for name in GLOBAL_ARTIFACT_NAMES:
        atomic_write_bytes(
            active[name],
            before[name],
        )


def verify_byte_exact_state(
    *,
    active: dict[str, Path],
    expected_hashes: dict[str, str],
) -> None:
    actual: dict[str, str] = {}

    for name in GLOBAL_ARTIFACT_NAMES:
        if not active[name].is_file():
            raise RuntimeError(
                "global_verify_artifact_missing:"
                f"{name}"
            )

        actual[name] = hashlib.sha256(
            active[name].read_bytes()
        ).hexdigest()

    if actual != expected_hashes:
        raise RuntimeError(
            "global_byte_exact_state_mismatch:"
            f"expected={expected_hashes}:"
            f"actual={actual}"
        )


def prepare_global_transaction(
    *,
    root: Path,
    market_session: str,
    market_generation_id: str,
    universe_generation_id: str,
) -> tuple[
    dict[str, Path],
    dict[str, Path],
    dict[str, bytes],
    dict[str, str],
    dict[str, Any],
]:
    active = active_artifact_paths(
        root
    )

    tx = global_transaction_paths(
        root
    )

    before = read_active_bytes(
        active
    )

    before_hashes = (
        hash_artifact_bytes(
            before
        )
    )

    transaction_root = tx[
        "transaction_root"
    ]

    transaction_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    fsync_directory(
        transaction_root.parent
    )

    existing_journal: (
        dict[str, Any] | None
    ) = None

    if tx["journal"].exists():
        loaded = json.loads(
            tx["journal"].read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            loaded,
            dict,
        ):
            raise RuntimeError(
                "global_journal_invalid"
            )

        existing_journal = loaded

        state = str(
            loaded.get("state")
            or ""
        )

        if state not in {
            "COMMITTED",
            "ROLLED_BACK",
            "RECOVERED_ROLLBACK",
        }:
            raise RuntimeError(
                "global_unresolved_transaction:"
                f"{state}"
            )

    backup_map = {
        "prices": tx[
            "backup_prices"
        ],
        "snapshot": tx[
            "backup_snapshot"
        ],
        "core": tx[
            "backup_core"
        ],
        "tactical": tx[
            "backup_tactical"
        ],
    }

    for name in GLOBAL_ARTIFACT_NAMES:
        atomic_write_bytes(
            backup_map[name],
            before[name],
            mode=0o660,
        )

        if (
            hashlib.sha256(
                backup_map[name]
                .read_bytes()
            ).hexdigest()
            != before_hashes[name]
        ):
            raise RuntimeError(
                "global_backup_hash_mismatch:"
                f"{name}"
            )

    journal: dict[str, Any] = {
        "schema_version": (
            GLOBAL_TRANSACTION_SCHEMA
        ),
        "artifact_type": (
            GLOBAL_TRANSACTION_TYPE
        ),
        "state": "PREPARED",
        "prepared_at": (
            market_authority.utc_now_iso()
        ),
        "committed_at": None,
        "rolled_back_at": None,
        "recovered_at": None,
        "market_session": (
            market_session
        ),
        "market_generation_id": (
            market_generation_id
        ),
        "universe_generation_id": (
            universe_generation_id
        ),
        "active": {
            name: str(active[name])
            for name
            in GLOBAL_ARTIFACT_NAMES
        },
        "backup": {
            name: str(
                backup_map[name]
            )
            for name
            in GLOBAL_ARTIFACT_NAMES
        },
        "before": before_hashes,
        "after": None,
    }

    atomic_write_json(
        tx["journal"],
        journal,
    )

    fsync_directory(
        transaction_root
    )

    return (
        active,
        tx,
        before,
        before_hashes,
        journal,
    )


def durable_global_activate(
    *,
    root: Path,
    prices: dict[str, Any],
    snapshot: dict[str, Any],
    core: dict[str, Any],
    tactical: dict[str, Any],
    fault_after: str | None = None,
) -> dict[str, Any]:
    validate_global_candidate(
        prices=prices,
        snapshot=snapshot,
        core=core,
        tactical=tactical,
    )

    market_session = str(
        prices["market_session"]
    )

    market_generation = str(
        prices["generation_id"]
    )

    universe_generation = str(
        core["generation_id"]
    )

    (
        active,
        tx,
        before,
        before_hashes,
        journal,
    ) = prepare_global_transaction(
        root=root,
        market_session=market_session,
        market_generation_id=(
            market_generation
        ),
        universe_generation_id=(
            universe_generation
        ),
    )

    candidate_bytes = (
        candidate_artifact_bytes(
            prices=prices,
            snapshot=snapshot,
            core=core,
            tactical=tactical,
        )
    )

    try:
        for name in (
            "prices",
            "snapshot",
            "core",
            "tactical",
        ):
            atomic_write_bytes(
                active[name],
                candidate_bytes[name],
            )

            journal["state"] = (
                f"{name.upper()}_WRITTEN"
            )

            atomic_write_json(
                tx["journal"],
                journal,
            )

            if fault_after == name:
                raise RuntimeError(
                    "synthetic_fault_after_"
                    f"{name}"
                )

        written = {
            name: json.loads(
                active[name].read_text(
                    encoding="utf-8"
                )
            )
            for name
            in GLOBAL_ARTIFACT_NAMES
        }

        validate_global_candidate(
            prices=written["prices"],
            snapshot=written[
                "snapshot"
            ],
            core=written["core"],
            tactical=written[
                "tactical"
            ],
        )

        after_hashes = {
            name: hashlib.sha256(
                active[name]
                .read_bytes()
            ).hexdigest()
            for name
            in GLOBAL_ARTIFACT_NAMES
        }

        journal["state"] = (
            "COMMITTED"
        )

        journal["committed_at"] = (
            market_authority.utc_now_iso()
        )

        journal["after"] = (
            after_hashes
        )

        atomic_write_json(
            tx["journal"],
            journal,
        )

        fsync_directory(
            tx["transaction_root"]
        )

        return {
            "status": "committed",
            "cutover_executed": True,
            "market_session": (
                market_session
            ),
            "market_generation_id": (
                market_generation
            ),
            "universe_generation_id": (
                universe_generation
            ),
            "before": before_hashes,
            "after": after_hashes,
            "journal": str(
                tx["journal"]
            ),
        }

    except BaseException:
        restore_global_before(
            active=active,
            before=before,
        )

        verify_byte_exact_state(
            active=active,
            expected_hashes=(
                before_hashes
            ),
        )

        journal["state"] = (
            "ROLLED_BACK"
        )

        journal["rolled_back_at"] = (
            market_authority.utc_now_iso()
        )

        journal["after"] = (
            before_hashes
        )

        atomic_write_json(
            tx["journal"],
            journal,
        )

        fsync_directory(
            tx["transaction_root"]
        )

        raise


def recover_global_transaction(
    *,
    root: Path,
) -> dict[str, Any]:
    active = active_artifact_paths(
        root
    )

    tx = global_transaction_paths(
        root
    )

    journal_path = tx[
        "journal"
    ]

    if not journal_path.exists():
        return {
            "status": (
                "no_recovery_needed"
            ),
            "recovered": False,
        }

    journal_raw = json.loads(
        journal_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        journal_raw,
        dict,
    ):
        raise RuntimeError(
            "global_recovery_journal_invalid"
        )

    journal = journal_raw

    if (
        journal.get(
            "schema_version"
        )
        != GLOBAL_TRANSACTION_SCHEMA
    ):
        raise RuntimeError(
            "global_recovery_schema_mismatch"
        )

    if (
        journal.get(
            "artifact_type"
        )
        != GLOBAL_TRANSACTION_TYPE
    ):
        raise RuntimeError(
            "global_recovery_type_mismatch"
        )

    state = str(
        journal.get("state")
        or ""
    )

    if state in {
        "COMMITTED",
        "ROLLED_BACK",
        "RECOVERED_ROLLBACK",
    }:
        return {
            "status": (
                "terminal_transaction"
            ),
            "state": state,
            "recovered": False,
        }

    recoverable_states = {
        "PREPARED",
        "PRICES_WRITTEN",
        "SNAPSHOT_WRITTEN",
        "CORE_WRITTEN",
        "TACTICAL_WRITTEN",
    }

    if state not in recoverable_states:
        raise RuntimeError(
            "global_recovery_unknown_state:"
            f"{state}"
        )

    before = journal.get(
        "before"
    )

    backup = journal.get(
        "backup"
    )

    recorded_active = (
        journal.get(
            "active"
        )
    )

    if not isinstance(
        before,
        dict,
    ):
        raise RuntimeError(
            "global_recovery_before_invalid"
        )

    if not isinstance(
        backup,
        dict,
    ):
        raise RuntimeError(
            "global_recovery_backup_invalid"
        )

    if not isinstance(
        recorded_active,
        dict,
    ):
        raise RuntimeError(
            "global_recovery_active_invalid"
        )

    expected_active = {
        name: str(active[name])
        for name
        in GLOBAL_ARTIFACT_NAMES
    }

    if (
        recorded_active
        != expected_active
    ):
        raise RuntimeError(
            "global_recovery_active_provenance_mismatch"
        )

    restore_bytes: (
        dict[str, bytes]
    ) = {}

    for name in GLOBAL_ARTIFACT_NAMES:
        backup_raw = backup.get(
            name
        )

        expected_hash = before.get(
            name
        )

        if (
            not isinstance(
                backup_raw,
                str,
            )
            or not backup_raw
        ):
            raise RuntimeError(
                "global_recovery_backup_path_invalid:"
                f"{name}"
            )

        backup_path = Path(
            backup_raw
        )

        expected_backup = tx[
            f"backup_{name}"
        ]

        if (
            backup_path
            != expected_backup
        ):
            raise RuntimeError(
                "global_recovery_backup_provenance_mismatch:"
                f"{name}"
            )

        if not backup_path.is_file():
            raise RuntimeError(
                "global_recovery_backup_missing:"
                f"{name}"
            )

        data = backup_path.read_bytes()

        if (
            not isinstance(
                expected_hash,
                str,
            )
            or hashlib.sha256(
                data
            ).hexdigest()
            != expected_hash
        ):
            raise RuntimeError(
                "global_recovery_backup_hash_mismatch:"
                f"{name}"
            )

        restore_bytes[name] = data

    # Only after ALL four backups have passed
    # provenance + hash validation may recovery
    # modify any active artifact.
    restore_global_before(
        active=active,
        before=restore_bytes,
    )

    verify_byte_exact_state(
        active=active,
        expected_hashes={
            name: str(
                before[name]
            )
            for name
            in GLOBAL_ARTIFACT_NAMES
        },
    )

    journal["state"] = (
        "RECOVERED_ROLLBACK"
    )

    journal["recovered_at"] = (
        market_authority.utc_now_iso()
    )

    journal["after"] = before

    atomic_write_json(
        journal_path,
        journal,
    )

    fsync_directory(
        tx["transaction_root"]
    )

    return {
        "status": (
            "recovered_rollback"
        ),
        "recovered": True,
        "restored": before,
    }


def main() -> int:
    args = parse_args()

    if (
        args.execute
        and not str(
            args.authorization_digest
            or ""
        ).strip()
    ):
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "mode": "execute",
                    "cutover_executed": False,
                    "active_files_modified": False,
                    "reason": (
                        "cutover_authorization_digest_missing"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 3

    if args.execute:
        paths = artifact_paths(
            args.root
        )

        PROVIDER_LOCK.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        CANONICAL_LOCK.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with PROVIDER_LOCK.open(
                "a+"
            ) as provider_lock:
                print(
                    "PROVIDER_LOCK=WAIT_SHARED",
                    file=sys.stderr,
                )

                fcntl.flock(
                    provider_lock.fileno(),
                    fcntl.LOCK_SH,
                )

                print(
                    "PROVIDER_LOCK=ACQUIRED_SHARED",
                    file=sys.stderr,
                )

                try:
                    with CANONICAL_LOCK.open(
                        "a+"
                    ) as canonical_lock:
                        print(
                            "CANONICAL_LOCK=WAIT_EXCLUSIVE",
                            file=sys.stderr,
                        )

                        fcntl.flock(
                            canonical_lock.fileno(),
                            fcntl.LOCK_EX,
                        )

                        print(
                            "CANONICAL_LOCK=ACQUIRED_EXCLUSIVE",
                            file=sys.stderr,
                        )

                        try:
                            pre_recovery_candidate = (
                                build_locked_candidate(
                                    paths
                                )
                            )

                            authorized_digest = (
                                validate_authorization_digest(
                                    pre_recovery_candidate,
                                    args.authorization_digest,
                                )
                            )

                            recovery = (
                                recover_global_transaction(
                                    root=args.root
                                )
                            )

                            candidate = (
                                build_locked_candidate(
                                    paths
                                )
                            )

                            post_recovery_digest = (
                                validate_authorization_digest(
                                    candidate,
                                    authorized_digest,
                                )
                            )

                            if (
                                post_recovery_digest
                                != authorized_digest
                            ):
                                raise RuntimeError(
                                    "cutover_authorization_changed_after_recovery"
                                )

                            payloads = candidate[
                                "candidate_payloads"
                            ]

                            transaction = (
                                durable_global_activate(
                                    root=args.root,
                                    prices=payloads[
                                        "prices"
                                    ],
                                    snapshot=payloads[
                                        "snapshot"
                                    ],
                                    core=payloads[
                                        "core"
                                    ],
                                    tactical=payloads[
                                        "tactical"
                                    ],
                                )
                            )

                        finally:
                            fcntl.flock(
                                canonical_lock.fileno(),
                                fcntl.LOCK_UN,
                            )

                            print(
                                "CANONICAL_LOCK=RELEASED_EXCLUSIVE",
                                file=sys.stderr,
                            )

                finally:
                    fcntl.flock(
                        provider_lock.fileno(),
                        fcntl.LOCK_UN,
                    )

                    print(
                        "PROVIDER_LOCK=RELEASED_SHARED",
                        file=sys.stderr,
                    )

        except Exception as exc:
            print(
                json.dumps(
                    {
                        "status": "blocked",
                        "mode": "execute",
                        "cutover_executed": False,
                        "active_files_modified": False,
                        "reason": (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )

            return 2

        report = public_report(
            candidate
        )

        report["mode"] = "execute"
        report["status"] = "committed"
        report["cutover_executed"] = True
        report["active_files_modified"] = True
        report["recovery"] = recovery
        report["transaction"] = transaction
        report["authorized_digest"] = (
            authorized_digest
        )

        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    paths = artifact_paths(
        args.root
    )

    PROVIDER_LOCK.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CANONICAL_LOCK.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with PROVIDER_LOCK.open(
            "a+"
        ) as provider_lock:
            print(
                "PROVIDER_LOCK=WAIT_SHARED",
                file=sys.stderr,
            )

            fcntl.flock(
                provider_lock.fileno(),
                fcntl.LOCK_SH,
            )

            print(
                "PROVIDER_LOCK=ACQUIRED_SHARED",
                file=sys.stderr,
            )

            try:
                with CANONICAL_LOCK.open(
                    "a+"
                ) as canonical_lock:
                    print(
                        "CANONICAL_LOCK=WAIT_EXCLUSIVE",
                        file=sys.stderr,
                    )

                    fcntl.flock(
                        canonical_lock.fileno(),
                        fcntl.LOCK_EX,
                    )

                    print(
                        "CANONICAL_LOCK=ACQUIRED_EXCLUSIVE",
                        file=sys.stderr,
                    )

                    try:
                        candidate = (
                            build_locked_candidate(
                                paths
                            )
                        )
                    finally:
                        fcntl.flock(
                            canonical_lock.fileno(),
                            fcntl.LOCK_UN,
                        )

                        print(
                            "CANONICAL_LOCK=RELEASED_EXCLUSIVE",
                            file=sys.stderr,
                        )

            finally:
                fcntl.flock(
                    provider_lock.fileno(),
                    fcntl.LOCK_UN,
                )

                print(
                    "PROVIDER_LOCK=RELEASED_SHARED",
                    file=sys.stderr,
                )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "mode": "dry_run",
                    "cutover_executed": False,
                    "active_files_modified": False,
                    "reason": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 2

    print(
        json.dumps(
            public_report(candidate),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
