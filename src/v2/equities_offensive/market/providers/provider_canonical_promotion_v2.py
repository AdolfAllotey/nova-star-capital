#!/usr/bin/env python3
"""
Nova Star Capital
Offensive Equities — Canonical Promotion Manager V2

Purpose
-------
Promote a strictly validated provider snapshot into the canonical
Offensive Equities market-data contract.

Safety model
------------
- dry-run by default;
- real promotion requires --execute;
- Quality Gate must be strict PASS;
- Quality Gate must explicitly authorize promotion;
- provider and validation artifacts must be recent;
- primary provider must be healthy;
- validation must be fully validated;
- exactly the expected universe must be present;
- all symbols must share one market session;
- every symbol must satisfy the canonical schema;
- active canonical artifacts are backed up before mutation;
- any write/verification failure rolls both canonical artifacts back.

This module does not execute trading, signals, orders or broker actions.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

PROVIDER_ROOT = DATA_ROOT / "market/providers"

PRIMARY_PATH = (
    PROVIDER_ROOT / "market_data_yfinance_v1.json"
)

VALIDATION_PATH = (
    PROVIDER_ROOT / "cross_source_validation_v1.json"
)

GATE_PATH = (
    PROVIDER_ROOT / "provider_quality_gate_v1.json"
)

ACTIVE_PRICES = (
    DATA_ROOT / "market/prices.json"
)

ACTIVE_SNAPSHOT = (
    DATA_ROOT / "universe/price_snapshot.json"
)

CANONICAL_LOCK = Path(
    "/run/lock/nsc-equities-offensive-canonical.lock"
)

REPORT_PATH = (
    PROVIDER_ROOT / "canonical_promotion_v2.json"
)

BACKUP_ROOT = (
    PROVIDER_ROOT / "canonical_backups"
)

EXPECTED_SYMBOL_COUNT = 15
# D1 economic freshness is governed by the latest completed
# authoritative XNYS session, not by wall-clock artifact age.
#
# Generated-at timestamps remain part of the causal-chain contract:
# primary provider <= cross-source validation <= quality gate.
MAX_CHAIN_CLOCK_SKEW_SECONDS = 1.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace(
        "+00:00",
        "Z",
    )


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def artifact_age_minutes(payload: dict[str, Any]) -> float | None:
    timestamp = parse_timestamp(
        payload.get("generated_at")
        or payload.get("ts")
    )

    if timestamp is None:
        return None

    return (
        utc_now() - timestamp
    ).total_seconds() / 60.0


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(
            f"required_artifact_missing:{path}"
        )

    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"invalid_json_root:{path}"
        )

    return payload


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )

    existing_mode: int | None = None

    if path.exists():
        existing_mode = (
            path.stat().st_mode & 0o7777
        )

    try:
        encoded = (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_TRUNC
        )

        fd = os.open(
            temporary,
            flags,
            0o660,
        )

        try:
            if existing_mode is not None:
                os.fchmod(
                    fd,
                    existing_mode,
                )

            with os.fdopen(
                fd,
                "wb",
                closefd=True,
            ) as handle:
                fd = -1

                handle.write(encoded)
                handle.flush()
                os.fsync(
                    handle.fileno()
                )
        finally:
            if fd >= 0:
                os.close(fd)

        os.replace(
            temporary,
            path,
        )

        directory_fd = os.open(
            path.parent,
            os.O_RDONLY
            | getattr(
                os,
                "O_DIRECTORY",
                0,
            ),
        )

        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if temporary.exists():
            temporary.unlink()


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


def safe_float(
    value: Any,
    *,
    positive: bool = False,
) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"invalid_numeric_value:{value!r}"
        ) from exc

    if not math.isfinite(converted):
        raise RuntimeError(
            f"non_finite_numeric_value:{value!r}"
        )

    if positive and converted <= 0:
        raise RuntimeError(
            f"non_positive_numeric_value:{value!r}"
        )

    return converted


def generated_at_datetime(
    payload: dict[str, Any],
) -> datetime | None:
    raw = payload.get("generated_at")

    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(raw).replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)


def latest_completed_xnys_session(
    now: datetime | None = None,
) -> str:
    """
    Return the latest fully completed XNYS session.

    The exchange_calendars session index and schedule remain
    authoritative for trading days and close times.

    Do not use the library's date/session parsing helpers here:
    exchange_calendars 4.11.3 with pandas 3.0.x can compare
    nanosecond Timestamp.value values against microsecond-backed
    sessions_nanos values and incorrectly classify valid dates as
    out of bounds.

    Fail closed if the calendar cannot establish a completed
    session or if the requested instant lies outside the loaded
    calendar horizon.
    """
    try:
        import exchange_calendars as xcals
        import pandas as pd
    except Exception as exc:
        raise RuntimeError(
            "xnys_calendar_dependency_unavailable"
        ) from exc

    if (
        now is not None
        and (
            now.tzinfo is None
            or now.utcoffset() is None
        )
    ):
        raise RuntimeError(
            "xnys_current_time_timezone_missing"
        )

    current = (
        now.astimezone(timezone.utc)
        if now is not None
        else datetime.now(timezone.utc)
    )

    try:
        calendar = xcals.get_calendar(
            "XNYS"
        )

        sessions = calendar.sessions
        schedule = calendar.schedule
    except Exception as exc:
        raise RuntimeError(
            "xnys_calendar_unavailable"
        ) from exc

    if len(sessions) == 0:
        raise RuntimeError(
            "xnys_calendar_empty"
        )

    current_ts = pd.Timestamp(
        current
    ).tz_convert(
        "UTC"
    )

    current_date = (
        current_ts
        .tz_localize(None)
        .normalize()
    )

    first_session = sessions[0]
    last_session = sessions[-1]

    if current_date < first_session:
        raise RuntimeError(
            "xnys_current_date_before_calendar"
        )

    if current_date > last_session:
        raise RuntimeError(
            "xnys_current_date_after_calendar"
        )

    insertion = sessions.searchsorted(
        current_date,
        side="right",
    )

    if insertion <= 0:
        raise RuntimeError(
            "xnys_previous_session_unavailable"
        )

    candidate_index = (
        insertion - 1
    )

    candidate = sessions[
        candidate_index
    ]

    try:
        close_ts = schedule.loc[
            candidate,
            "close",
        ]
    except Exception as exc:
        raise RuntimeError(
            "xnys_session_close_unavailable"
        ) from exc

    if pd.isna(close_ts):
        raise RuntimeError(
            "xnys_session_close_unavailable"
        )

    if current_ts < close_ts:
        candidate_index -= 1

        if candidate_index < 0:
            raise RuntimeError(
                "xnys_completed_session_unavailable"
            )

        candidate = sessions[
            candidate_index
        ]

    return str(
        candidate.date()
    )

def normalized_symbol_set(
    payload: dict[str, Any],
) -> set[str]:
    symbols = payload.get("symbols")

    if not isinstance(symbols, dict):
        return set()

    return {
        str(symbol).upper()
        for symbol in symbols
    }


def validate_inputs(
    primary: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []

    if primary.get("status") != "healthy":
        blockers.append(
            "primary_provider_not_healthy"
        )

    primary_symbols = primary.get("symbols")

    if not isinstance(primary_symbols, dict):
        primary_symbols = {}

    validation_symbols = validation.get("symbols")

    if not isinstance(validation_symbols, dict):
        validation_symbols = {}

    if validation.get("status") != "validated":
        blockers.append(
            "cross_source_validation_not_validated"
        )

    if gate.get("decision") != "PASS":
        blockers.append(
            "quality_gate_not_pass"
        )

    promotion = gate.get("promotion")

    if not isinstance(promotion, dict):
        promotion = {}

    if (
        promotion.get(
            "authorized_by_quality_gate"
        )
        is not True
    ):
        blockers.append(
            "quality_gate_not_authorized"
        )

    primary_generated = generated_at_datetime(
        primary
    )

    validation_generated = generated_at_datetime(
        validation
    )

    gate_generated = generated_at_datetime(
        gate
    )

    generated_chain = {
        "primary": primary_generated,
        "validation": validation_generated,
        "quality_gate": gate_generated,
    }

    now = datetime.now(timezone.utc)

    for name, generated in generated_chain.items():
        if generated is None:
            blockers.append(
                f"{name}_timestamp_missing_or_invalid"
            )
        elif (
            generated - now
        ).total_seconds() > MAX_CHAIN_CLOCK_SKEW_SECONDS:
            blockers.append(
                f"{name}_timestamp_in_future"
            )

    if (
        primary_generated is not None
        and validation_generated is not None
        and (
            primary_generated
            - validation_generated
        ).total_seconds()
        > MAX_CHAIN_CLOCK_SKEW_SECONDS
    ):
        blockers.append(
            "validation_predates_primary_provider"
        )

    if (
        validation_generated is not None
        and gate_generated is not None
        and (
            validation_generated
            - gate_generated
        ).total_seconds()
        > MAX_CHAIN_CLOCK_SKEW_SECONDS
    ):
        blockers.append(
            "quality_gate_predates_validation"
        )

    try:
        expected_market_session = (
            latest_completed_xnys_session(
                now
            )
        )
    except Exception:
        expected_market_session = None
        blockers.append(
            "xnys_completed_session_unavailable"
        )

    primary_set = normalized_symbol_set(
        primary
    )

    validation_set = normalized_symbol_set(
        validation
    )

    if len(primary_set) != EXPECTED_SYMBOL_COUNT:
        blockers.append(
            "primary_symbol_count_not_15"
        )

    if len(validation_set) != EXPECTED_SYMBOL_COUNT:
        blockers.append(
            "validation_symbol_count_not_15"
        )

    if primary_set != validation_set:
        blockers.append(
            "primary_validation_universe_mismatch"
        )

    session_dates: set[str] = set()

    for symbol in sorted(primary_set):
        row = primary_symbols.get(symbol)

        if not isinstance(row, dict):
            blockers.append(
                f"{symbol}:primary_row_invalid"
            )
            continue

        session_date = row.get(
            "last_session_date"
        )

        if not session_date:
            blockers.append(
                f"{symbol}:last_session_date_missing"
            )
        else:
            session_dates.add(
                str(session_date)
            )

        validation_row = validation_symbols.get(
            symbol
        )

        if not isinstance(
            validation_row,
            dict,
        ):
            blockers.append(
                f"{symbol}:validation_row_invalid"
            )
            continue

        if (
            validation_row.get("status")
            != "validated"
        ):
            blockers.append(
                f"{symbol}:not_cross_source_validated"
            )

        confidence = validation_row.get(
            "confidence_score"
        )

        try:
            confidence_value = float(
                confidence
            )
        except (TypeError, ValueError):
            blockers.append(
                f"{symbol}:confidence_invalid"
            )
        else:
            if confidence_value < 95.0:
                blockers.append(
                    f"{symbol}:confidence_below_95"
                )

    if len(session_dates) != 1:
        blockers.append(
            "primary_market_session_not_uniform"
        )

    actual_market_session = (
        next(iter(session_dates))
        if len(session_dates) == 1
        else None
    )

    if (
        expected_market_session is not None
        and actual_market_session is not None
        and actual_market_session
        != expected_market_session
    ):
        blockers.append(
            "primary_market_session_not_latest_completed_xnys"
        )

    return {
        "blockers": blockers,
        "temporal_contract": {
            "basis": "latest_completed_xnys_session",
            "expected_market_session": (
                expected_market_session
            ),
            "actual_market_session": (
                actual_market_session
            ),
            "primary_generated_at": (
                primary.get("generated_at")
            ),
            "validation_generated_at": (
                validation.get("generated_at")
            ),
            "quality_gate_generated_at": (
                gate.get("generated_at")
            ),
        },
        "symbol_count": len(primary_set),
        "symbols": sorted(primary_set),
        "market_session": actual_market_session,
    }


def build_canonical_artifacts(
    primary: dict[str, Any],
    validation: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    primary_symbols = primary.get("symbols")

    validation_symbols = validation.get(
        "symbols"
    )

    if not isinstance(primary_symbols, dict):
        raise RuntimeError(
            "primary_symbols_invalid"
        )

    if not isinstance(
        validation_symbols,
        dict,
    ):
        raise RuntimeError(
            "validation_symbols_invalid"
        )

    # Candidate identity must be reproducible from causal
    # provider inputs. Wall-clock build time must not alter
    # byte-exact authorization.
    generated_at = str(
        validation.get("generated_at") or ""
    ).strip()

    if not generated_at:
        raise RuntimeError(
            "validation_generated_at_missing"
        )

    prices: dict[str, float] = {}
    snapshot_prices: dict[str, Any] = {}

    market_sessions: set[str] = set()

    for symbol in sorted(primary_symbols):
        row = primary_symbols[symbol]

        if not isinstance(row, dict):
            raise RuntimeError(
                f"{symbol}:primary_row_invalid"
            )

        validation_row = (
            validation_symbols.get(symbol)
        )

        if not isinstance(
            validation_row,
            dict,
        ):
            raise RuntimeError(
                f"{symbol}:validation_row_invalid"
            )

        close_raw = (
            row.get("adjusted_close")
            if row.get("adjusted_close")
            is not None
            else row.get("close")
        )

        close = safe_float(
            close_raw,
            positive=True,
        )

        ma20 = safe_float(
            row.get("ma20"),
            positive=True,
        )

        ma50 = safe_float(
            row.get("ma50"),
            positive=True,
        )

        ma200 = safe_float(
            row.get("ma200"),
            positive=True,
        )

        hh_20 = safe_float(
            row.get("high20"),
            positive=True,
        )

        ll_20 = safe_float(
            row.get("low20"),
            positive=True,
        )

        ret_20 = safe_float(
            row.get("return20")
        )

        vol_ratio = safe_float(
            row.get("relative_volume"),
            positive=True,
        )

        volume = safe_float(
            row.get("volume"),
            positive=True,
        )

        history_days_raw = row.get(
            "history_rows"
        )

        try:
            history_days = int(
                history_days_raw
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"{symbol}:history_rows_invalid"
            ) from exc

        if history_days < 200:
            raise RuntimeError(
                f"{symbol}:insufficient_history"
            )

        last_market_date = row.get(
            "last_session_date"
        )

        if not last_market_date:
            raise RuntimeError(
                f"{symbol}:last_session_date_missing"
            )

        last_market_date = str(
            last_market_date
        )

        market_sessions.add(
            last_market_date
        )

        if (
            validation_row.get("status")
            != "validated"
        ):
            raise RuntimeError(
                f"{symbol}:validation_not_validated"
            )

        confidence = safe_float(
            validation_row.get(
                "confidence_score"
            )
        )

        if confidence < 95.0:
            raise RuntimeError(
                f"{symbol}:confidence_below_95"
            )

        prices[symbol] = round(
            close,
            8,
        )

        snapshot_prices[symbol] = {
            "close": round(close, 8),
            "ma20": round(ma20, 8),
            "ma50": round(ma50, 8),
            "ma200": round(ma200, 8),
            "hh_20": round(hh_20, 8),
            "ll_20": round(ll_20, 8),
            "ret_20": round(ret_20, 8),
            "vol_ratio": round(
                vol_ratio,
                8,
            ),
            "volume": round(volume, 8),
            "history_days": history_days,
            "last_market_date": (
                last_market_date
            ),
            "source": primary.get(
                "provider"
            ),
            "validation_status": (
                validation_row.get("status")
            ),
            "confidence_score": round(
                confidence,
                6,
            ),
        }

    if len(prices) != EXPECTED_SYMBOL_COUNT:
        raise RuntimeError(
            "canonical_symbol_count_not_15"
        )

    if len(market_sessions) != 1:
        raise RuntimeError(
            "canonical_market_session_not_uniform"
        )

    session = next(
        iter(market_sessions)
    )

    generation_material = {
        "market_session": session,
        "provider": primary.get("provider"),
        "provider_generated_at": (
            primary.get("generated_at")
        ),
        "validation_generated_at": (
            validation.get("generated_at")
        ),
    }

    generation_id = hashlib.sha256(
        json.dumps(
            generation_material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    common = {
        "ts": generated_at,
        "generation_id": generation_id,
        "source": primary.get(
            "provider"
        ),
        "universe": "nasdaq_core",
        "status": "active_simulated",
        "canonical": True,
        "symbol_count": len(prices),
        "market_session": session,
        "provider_generated_at": (
            primary.get("generated_at")
        ),
        "validation_generated_at": (
            validation.get("generated_at")
        ),
    }

    prices_payload = {
        **common,
        "engine": (
            "offensive_canonical_market_feed_v2"
        ),
        "prices": prices,
    }

    snapshot_payload = {
        **common,
        "engine": (
            "offensive_canonical_snapshot_v2"
        ),
        "prices": snapshot_prices,
    }

    return (
        prices_payload,
        snapshot_payload,
    )


def verify_written_contract(
    prices_path: Path,
    snapshot_path: Path,
    expected_session: str,
) -> None:
    prices = read_json(
        prices_path
    )

    snapshot = read_json(
        snapshot_path
    )

    if prices.get("canonical") is not True:
        raise RuntimeError(
            "prices_not_canonical"
        )

    if snapshot.get("canonical") is not True:
        raise RuntimeError(
            "snapshot_not_canonical"
        )

    price_rows = prices.get("prices")
    snapshot_rows = snapshot.get("prices")

    if not isinstance(price_rows, dict):
        raise RuntimeError(
            "prices_contract_invalid"
        )

    if not isinstance(snapshot_rows, dict):
        raise RuntimeError(
            "snapshot_contract_invalid"
        )

    if len(price_rows) != EXPECTED_SYMBOL_COUNT:
        raise RuntimeError(
            "prices_symbol_count_invalid"
        )

    if len(snapshot_rows) != EXPECTED_SYMBOL_COUNT:
        raise RuntimeError(
            "snapshot_symbol_count_invalid"
        )

    if set(price_rows) != set(snapshot_rows):
        raise RuntimeError(
            "canonical_universe_mismatch"
        )

    if (
        prices.get("market_session")
        != expected_session
    ):
        raise RuntimeError(
            "prices_market_session_mismatch"
        )

    if (
        snapshot.get("market_session")
        != expected_session
    ):
        raise RuntimeError(
            "snapshot_market_session_mismatch"
        )

    prices_generation = prices.get(
        "generation_id"
    )

    snapshot_generation = snapshot.get(
        "generation_id"
    )

    if (
        not isinstance(prices_generation, str)
        or not prices_generation.strip()
    ):
        raise RuntimeError(
            "prices_generation_id_invalid"
        )

    if (
        not isinstance(snapshot_generation, str)
        or not snapshot_generation.strip()
    ):
        raise RuntimeError(
            "snapshot_generation_id_invalid"
        )

    if prices_generation != snapshot_generation:
        raise RuntimeError(
            "canonical_generation_id_mismatch"
        )

    required = {
        "close",
        "ma20",
        "ma50",
        "ma200",
        "hh_20",
        "ll_20",
        "ret_20",
        "vol_ratio",
        "volume",
        "history_days",
        "last_market_date",
        "source",
    }

    for symbol, row in snapshot_rows.items():
        if not isinstance(row, dict):
            raise RuntimeError(
                f"{symbol}:snapshot_row_invalid"
            )

        missing = sorted(
            required - set(row)
        )

        if missing:
            raise RuntimeError(
                f"{symbol}:missing_fields:{missing}"
            )

        if (
            row.get("last_market_date")
            != expected_session
        ):
            raise RuntimeError(
                f"{symbol}:market_session_mismatch"
            )



def fsync_directory(
    directory: Path,
) -> None:
    directory_fd = os.open(
        directory,
        os.O_RDONLY
        | getattr(
            os,
            "O_DIRECTORY",
            0,
        ),
    )

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def durable_copy_file(
    source: Path,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_name(
        f".{destination.name}.{os.getpid()}.tmp"
    )

    source_stat = source.stat()

    try:
        with source.open("rb") as source_handle:
            fd = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_TRUNC,
                source_stat.st_mode & 0o7777,
            )

            try:
                os.fchmod(
                    fd,
                    source_stat.st_mode & 0o7777,
                )

                with os.fdopen(
                    fd,
                    "wb",
                    closefd=True,
                ) as destination_handle:
                    fd = -1

                    shutil.copyfileobj(
                        source_handle,
                        destination_handle,
                    )

                    destination_handle.flush()
                    os.fsync(
                        destination_handle.fileno()
                    )
            finally:
                if fd >= 0:
                    os.close(fd)

        os.replace(
            temporary,
            destination,
        )

        fsync_directory(
            destination.parent
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def restore_file(
    backup: Path | None,
    target: Path,
    existed_before: bool,
) -> None:
    if backup is not None and backup.exists():
        durable_copy_file(
            backup,
            target,
        )
        return

    if not existed_before and target.exists():
        target.unlink()

        fsync_directory(
            target.parent
        )



def recover_incomplete_transactions(
    *,
    active_prices: Path = ACTIVE_PRICES,
    active_snapshot: Path = ACTIVE_SNAPSHOT,
    backup_root: Path = BACKUP_ROOT,
) -> list[dict[str, Any]]:
    if not backup_root.exists():
        return []

    recovered: list[dict[str, Any]] = []

    journal_paths = sorted(
        backup_root.glob(
            "*/transaction.json"
        )
    )

    # Global recovery preflight. Nothing below this
    # point may mutate active canonical files until
    # ambiguity and transaction provenance have been
    # ruled out for the complete journal set.
    prepared_journals: list[
        tuple[Path, dict[str, Any]]
    ] = []

    terminal_states = {
        "COMMITTED",
        "ROLLED_BACK",
        "RECOVERED_ROLLBACK",
    }

    for candidate_path in journal_paths:
        candidate = read_json(
            candidate_path
        )

        candidate_state = candidate.get(
            "state"
        )

        if candidate_state in terminal_states:
            continue

        if candidate_state != "PREPARED":
            raise RuntimeError(
                "unknown_transaction_state:"
                f"{candidate_state}:"
                f"{candidate_path}"
            )

        prepared_journals.append(
            (
                candidate_path,
                candidate,
            )
        )

    if len(prepared_journals) > 1:
        raise RuntimeError(
            "multiple_prepared_transactions"
        )

    if prepared_journals:
        (
            prepared_path,
            prepared,
        ) = prepared_journals[0]

        transaction_dir = (
            prepared_path.parent
        )

        transaction_id = prepared.get(
            "transaction_id"
        )

        if (
            not isinstance(
                transaction_id,
                str,
            )
            or not transaction_id
            or transaction_id
            != transaction_dir.name
        ):
            raise RuntimeError(
                "recovery_transaction_id_mismatch"
            )

        if (
            prepared.get("schema_version")
            != "1.0"
        ):
            raise RuntimeError(
                "recovery_schema_version_mismatch"
            )

        if (
            prepared.get("artifact_type")
            != "offensive_canonical_transaction"
        ):
            raise RuntimeError(
                "recovery_artifact_type_mismatch"
            )

        generation_id = prepared.get(
            "generation_id"
        )

        if (
            not isinstance(
                generation_id,
                str,
            )
            or len(generation_id) != 64
            or any(
                char not in "0123456789abcdef"
                for char in generation_id
            )
        ):
            raise RuntimeError(
                "recovery_generation_id_invalid"
            )

        market_session = prepared.get(
            "market_session"
        )

        if (
            not isinstance(
                market_session,
                str,
            )
            or not market_session
        ):
            raise RuntimeError(
                "recovery_market_session_invalid"
            )

        prepared_backup = (
            prepared.get("backup")
            or {}
        )

        expected_prices_backup = (
            transaction_dir
            / "prices.json"
        )

        expected_snapshot_backup = (
            transaction_dir
            / "price_snapshot.json"
        )

        if (
            prepared_backup.get("prices")
            != str(expected_prices_backup)
        ):
            raise RuntimeError(
                "recovery_prices_backup_provenance_mismatch"
            )

        if (
            prepared_backup.get("snapshot")
            != str(expected_snapshot_backup)
        ):
            raise RuntimeError(
                "recovery_snapshot_backup_provenance_mismatch"
            )

    for journal_path in journal_paths:
        journal = read_json(
            journal_path
        )

        state = journal.get("state")

        if state in {
            "COMMITTED",
            "ROLLED_BACK",
            "RECOVERED_ROLLBACK",
        }:
            continue

        if state != "PREPARED":
            raise RuntimeError(
                "unknown_transaction_state:"
                f"{state}:"
                f"{journal_path}"
            )

        recorded_active = (
            journal.get("active")
            or {}
        )

        if (
            recorded_active.get("prices")
            != str(active_prices)
        ):
            raise RuntimeError(
                "recovery_active_prices_mismatch"
            )

        if (
            recorded_active.get("snapshot")
            != str(active_snapshot)
        ):
            raise RuntimeError(
                "recovery_active_snapshot_mismatch"
            )

        backup = (
            journal.get("backup")
            or {}
        )

        existed_before = (
            journal.get(
                "existed_before"
            )
            or {}
        )

        before = (
            journal.get("before")
            or {}
        )

        prices_backup_raw = (
            backup.get("prices")
        )
        snapshot_backup_raw = (
            backup.get("snapshot")
        )

        prices_existed = bool(
            existed_before.get(
                "prices"
            )
        )

        snapshot_existed = bool(
            existed_before.get(
                "snapshot"
            )
        )

        prices_backup = (
            Path(prices_backup_raw)
            if prices_backup_raw
            else None
        )

        snapshot_backup = (
            Path(snapshot_backup_raw)
            if snapshot_backup_raw
            else None
        )

        if (
            prices_existed
            and (
                prices_backup is None
                or not prices_backup.is_file()
            )
        ):
            raise RuntimeError(
                "recovery_prices_backup_missing"
            )

        if (
            snapshot_existed
            and (
                snapshot_backup is None
                or not snapshot_backup.is_file()
            )
        ):
            raise RuntimeError(
                "recovery_snapshot_backup_missing"
            )

        if prices_existed:
            expected = before.get(
                "prices_sha256"
            )

            if (
                not isinstance(
                    expected,
                    str,
                )
                or not expected
            ):
                raise RuntimeError(
                    "recovery_prices_before_hash_missing"
                )

            if (
                sha256_file(
                    prices_backup
                )
                != expected
            ):
                raise RuntimeError(
                    "recovery_prices_backup_hash_mismatch"
                )

        if snapshot_existed:
            expected = before.get(
                "snapshot_sha256"
            )

            if (
                not isinstance(
                    expected,
                    str,
                )
                or not expected
            ):
                raise RuntimeError(
                    "recovery_snapshot_before_hash_missing"
                )

            if (
                sha256_file(
                    snapshot_backup
                )
                != expected
            ):
                raise RuntimeError(
                    "recovery_snapshot_backup_hash_mismatch"
                )

        # Conservative crash recovery:
        # never complete a partial promotion.
        # Restore BOTH members to their
        # pre-transaction state.
        restore_file(
            prices_backup,
            active_prices,
            prices_existed,
        )

        restore_file(
            snapshot_backup,
            active_snapshot,
            snapshot_existed,
        )

        restored = {
            "prices_sha256": (
                sha256_file(
                    active_prices
                )
            ),
            "snapshot_sha256": (
                sha256_file(
                    active_snapshot
                )
            ),
        }

        if restored != before:
            raise RuntimeError(
                "recovery_restored_hash_mismatch"
            )

        journal[
            "state"
        ] = "RECOVERED_ROLLBACK"

        journal[
            "recovered_at"
        ] = utc_now_iso()

        journal[
            "after"
        ] = restored

        atomic_write_json(
            journal_path,
            journal,
        )

        recovered.append(
            {
                "transaction_id": (
                    journal.get(
                        "transaction_id"
                    )
                ),
                "journal_path": str(
                    journal_path
                ),
                "state": (
                    "RECOVERED_ROLLBACK"
                ),
                "restored": restored,
            }
        )

    return recovered


def execute_transaction(
    prices_payload: dict[str, Any],
    snapshot_payload: dict[str, Any],
    market_session: str,
    *,
    active_prices: Path = ACTIVE_PRICES,
    active_snapshot: Path = ACTIVE_SNAPSHOT,
    backup_root: Path = BACKUP_ROOT,
) -> dict[str, Any]:
    stamp = utc_now().strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    generation_id = prices_payload.get(
        "generation_id"
    )

    if (
        not isinstance(generation_id, str)
        or not generation_id.strip()
    ):
        raise RuntimeError(
            "transaction_generation_id_invalid"
        )

    if (
        snapshot_payload.get("generation_id")
        != generation_id
    ):
        raise RuntimeError(
            "transaction_generation_id_mismatch"
        )

    transaction_id = (
        f"{stamp}-{generation_id[:16]}"
    )

    if not backup_root.parent.is_dir():
        raise RuntimeError(
            "backup_root_parent_missing"
        )

    if backup_root.exists():
        if not backup_root.is_dir():
            raise RuntimeError(
                "backup_root_not_directory"
            )
    else:
        backup_root.mkdir()

        # Persist BACKUP_ROOT itself in its
        # already-existing parent before
        # placing transaction state below it.
        fsync_directory(
            backup_root.parent
        )

    backup_dir = (
        backup_root / transaction_id
    )

    backup_dir.mkdir(
        exist_ok=False,
    )

    # Persist the transaction directory entry
    # in the now-durable BACKUP_ROOT.
    fsync_directory(
        backup_root
    )

    journal_path = (
        backup_dir / "transaction.json"
    )

    prices_existed = (
        active_prices.exists()
    )

    snapshot_existed = (
        active_snapshot.exists()
    )

    before = {
        "prices_sha256": (
            sha256_file(active_prices)
        ),
        "snapshot_sha256": (
            sha256_file(active_snapshot)
        ),
    }

    prices_backup: Path | None = None
    snapshot_backup: Path | None = None

    if prices_existed:
        prices_backup = (
            backup_dir / "prices.json"
        )

        durable_copy_file(
            active_prices,
            prices_backup,
        )

        if (
            sha256_file(prices_backup)
            != before["prices_sha256"]
        ):
            raise RuntimeError(
                "prices_backup_hash_mismatch"
            )

    if snapshot_existed:
        snapshot_backup = (
            backup_dir
            / "price_snapshot.json"
        )

        durable_copy_file(
            active_snapshot,
            snapshot_backup,
        )

        if (
            sha256_file(snapshot_backup)
            != before["snapshot_sha256"]
        ):
            raise RuntimeError(
                "snapshot_backup_hash_mismatch"
            )

    prepared_at = utc_now_iso()

    journal: dict[str, Any] = {
        "schema_version": "1.0",
        "artifact_type": (
            "offensive_canonical_transaction"
        ),
        "transaction_id": transaction_id,
        "generation_id": generation_id,
        "market_session": market_session,
        "state": "PREPARED",
        "prepared_at": prepared_at,
        "committed_at": None,
        "recovered_at": None,
        "active": {
            "prices": str(active_prices),
            "snapshot": str(
                active_snapshot
            ),
        },
        "backup": {
            "prices": (
                str(prices_backup)
                if prices_backup is not None
                else None
            ),
            "snapshot": (
                str(snapshot_backup)
                if snapshot_backup is not None
                else None
            ),
        },
        "existed_before": {
            "prices": prices_existed,
            "snapshot": snapshot_existed,
        },
        "before": before,
        "after": None,
    }

    atomic_write_json(
        journal_path,
        journal,
    )

    try:
        atomic_write_json(
            active_prices,
            prices_payload,
        )

        atomic_write_json(
            active_snapshot,
            snapshot_payload,
        )

        verify_written_contract(
            active_prices,
            active_snapshot,
            market_session,
        )

        after = {
            "prices_sha256": (
                sha256_file(
                    active_prices
                )
            ),
            "snapshot_sha256": (
                sha256_file(
                    active_snapshot
                )
            ),
        }

        journal["state"] = "COMMITTED"
        journal["committed_at"] = (
            utc_now_iso()
        )
        journal["after"] = after

        atomic_write_json(
            journal_path,
            journal,
        )

    except Exception:
        restore_file(
            prices_backup,
            active_prices,
            prices_existed,
        )

        restore_file(
            snapshot_backup,
            active_snapshot,
            snapshot_existed,
        )

        restored = {
            "prices_sha256": (
                sha256_file(
                    active_prices
                )
            ),
            "snapshot_sha256": (
                sha256_file(
                    active_snapshot
                )
            ),
        }

        if restored != before:
            raise RuntimeError(
                "transaction_rollback_hash_mismatch"
            )

        journal["state"] = "ROLLED_BACK"
        journal["recovered_at"] = (
            utc_now_iso()
        )
        journal["after"] = restored

        atomic_write_json(
            journal_path,
            journal,
        )

        raise

    return {
        "transaction_id": transaction_id,
        "generation_id": generation_id,
        "journal_path": str(
            journal_path
        ),
        "backup_dir": str(
            backup_dir
        ),
        "state": journal["state"],
        "before": before,
        "after": journal["after"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Promote validated provider data "
            "into the active canonical files."
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=REPORT_PATH,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.execute:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "mode": "execute",
                    "promotion_executed": False,
                    "active_files_modified": False,
                    "reason": "standalone_market_execute_disabled_use_global_four_artifact_cutover",
                    "required_authority": (
                        "four_artifact_cutover_v2"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 3


    report: dict[str, Any] = {
        "schema_version": "2.0",
        "artifact_type": (
            "offensive_equities_canonical_promotion"
        ),
        "generated_at": utc_now_iso(),
        "mode": (
            "execute"
            if args.execute
            else "dry_run"
        ),
        "promotion_executed": False,
        "canonical_files_modified": False,
    }

    try:
        primary = read_json(
            PRIMARY_PATH
        )

        validation = read_json(
            VALIDATION_PATH
        )

        gate = read_json(
            GATE_PATH
        )

        validation_result = validate_inputs(
            primary,
            validation,
            gate,
        )

        report["validation"] = (
            validation_result
        )

        blockers = validation_result[
            "blockers"
        ]

        if blockers:
            report["status"] = "blocked"
            report["blockers"] = blockers

            atomic_write_json(
                args.report,
                report,
            )

            print(
                json.dumps(
                    report,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            return 2

        (
            prices_payload,
            snapshot_payload,
        ) = build_canonical_artifacts(
            primary,
            validation,
        )

        session = validation_result[
            "market_session"
        ]

        report["candidate"] = {
            "market_session": session,
            "symbol_count": (
                len(
                    prices_payload[
                        "prices"
                    ]
                )
            ),
            "prices_engine": (
                prices_payload["engine"]
            ),
            "snapshot_engine": (
                snapshot_payload["engine"]
            ),
            "aapl_price": (
                prices_payload[
                    "prices"
                ].get("AAPL")
            ),
            "aapl_snapshot": (
                snapshot_payload[
                    "prices"
                ].get("AAPL")
            ),
        }

        if not args.execute:
            report["status"] = (
                "dry_run_ready"
            )
            report["blockers"] = []

            atomic_write_json(
                args.report,
                report,
            )

            print(
                json.dumps(
                    report,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            return 0

        CANONICAL_LOCK.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with CANONICAL_LOCK.open("a+") as lock_handle:
            print(
                "CANONICAL_LOCK=WAIT_EXCLUSIVE"
            )

            fcntl.flock(
                lock_handle.fileno(),
                fcntl.LOCK_EX,
            )

            print(
                "CANONICAL_LOCK=ACQUIRED_EXCLUSIVE"
            )

            try:
                # A previous writer may have died after
                # durable PREPARED and before COMMITTED.
                # Recovery is mandatory while LOCK_EX is held
                # and before any new provider authorization.
                recovered_transactions = (
                    recover_incomplete_transactions()
                )

                report[
                    "recovered_transactions"
                ] = recovered_transactions

                # Execute authorization is based exclusively
                # on artifacts re-read while holding LOCK_EX.
                locked_primary = read_json(
                    PRIMARY_PATH
                )

                locked_validation = read_json(
                    VALIDATION_PATH
                )

                locked_gate = read_json(
                    GATE_PATH
                )

                locked_validation_result = (
                    validate_inputs(
                        locked_primary,
                        locked_validation,
                        locked_gate,
                    )
                )

                locked_blockers = (
                    locked_validation_result[
                        "blockers"
                    ]
                )

                if locked_blockers:
                    raise RuntimeError(
                        "locked_revalidation_blocked:"
                        + ",".join(
                            str(item)
                            for item
                            in locked_blockers
                        )
                    )

                (
                    locked_prices_payload,
                    locked_snapshot_payload,
                ) = build_canonical_artifacts(
                    locked_primary,
                    locked_validation,
                )

                locked_session = (
                    locked_validation_result[
                        "market_session"
                    ]
                )

                if not locked_session:
                    raise RuntimeError(
                        "locked_market_session_missing"
                    )

                report[
                    "locked_validation"
                ] = locked_validation_result

                report[
                    "locked_candidate"
                ] = {
                    "market_session": (
                        locked_session
                    ),
                    "symbol_count": len(
                        locked_prices_payload[
                            "prices"
                        ]
                    ),
                    "generation_id": (
                        locked_prices_payload.get(
                            "generation_id"
                        )
                    ),
                    "prices_engine": (
                        locked_prices_payload[
                            "engine"
                        ]
                    ),
                    "snapshot_engine": (
                        locked_snapshot_payload[
                            "engine"
                        ]
                    ),
                }

                transaction = execute_transaction(
                    locked_prices_payload,
                    locked_snapshot_payload,
                    str(locked_session),
                )
            finally:
                fcntl.flock(
                    lock_handle.fileno(),
                    fcntl.LOCK_UN,
                )

                print(
                    "CANONICAL_LOCK=RELEASED_EXCLUSIVE"
                )

        report["status"] = "promoted"
        report["promotion_executed"] = True
        report[
            "canonical_files_modified"
        ] = True
        report["transaction"] = transaction
        report["blockers"] = []

        atomic_write_json(
            args.report,
            report,
        )

        print(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            )
        )

        return 0

    except Exception as exc:
        report["status"] = "failed"
        report["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

        try:
            atomic_write_json(
                args.report,
                report,
            )
        except Exception:
            pass

        print(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
