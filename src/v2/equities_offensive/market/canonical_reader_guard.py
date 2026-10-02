from __future__ import annotations

from datetime import datetime, timezone

import argparse
import json
from pathlib import Path

from src.v2.equities_offensive.market.providers.provider_session_clock import (
    latest_completed_xnys_session,
)
from typing import Any


DATA_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)

ACTIVE_PRICES = (
    DATA_ROOT / "market/prices.json"
)

ACTIVE_SNAPSHOT = (
    DATA_ROOT / "universe/price_snapshot.json"
)

BACKUP_ROOT = (
    DATA_ROOT
    / "market/providers/canonical_backups"
)

LEGACY_PRICES_ENGINE = (
    "offensive_canonical_market_feed_v1"
)

LEGACY_SNAPSHOT_ENGINE = (
    "offensive_canonical_snapshot_v1"
)


def read_json(
    path: Path,
) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"canonical_not_object:{path}"
        )

    return payload


def assert_no_prepared_transaction(
    backup_root: Path,
) -> None:
    if not backup_root.exists():
        return

    for journal_path in sorted(
        backup_root.glob(
            "*/transaction.json"
        )
    ):
        journal = read_json(
            journal_path
        )

        state = journal.get("state")

        if state == "PREPARED":
            raise RuntimeError(
                "canonical_prepared_transaction:"
                f"{journal_path}"
            )

        if state not in {
            "COMMITTED",
            "ROLLED_BACK",
            "RECOVERED_ROLLBACK",
        }:
            raise RuntimeError(
                "canonical_unknown_transaction_state:"
                f"{state}:"
                f"{journal_path}"
            )


def validate_legacy_pair(
    prices: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if (
        prices.get("engine")
        != LEGACY_PRICES_ENGINE
    ):
        raise RuntimeError(
            "legacy_prices_engine_invalid"
        )

    if (
        snapshot.get("engine")
        != LEGACY_SNAPSHOT_ENGINE
    ):
        raise RuntimeError(
            "legacy_snapshot_engine_invalid"
        )

    prices_ts = prices.get("ts")
    snapshot_ts = snapshot.get("ts")

    if (
        not isinstance(prices_ts, str)
        or not prices_ts
        or prices_ts != snapshot_ts
    ):
        raise RuntimeError(
            "legacy_pair_timestamp_mismatch"
        )

    prices_universe = prices.get(
        "universe"
    )
    snapshot_universe = snapshot.get(
        "universe"
    )

    if (
        not isinstance(
            prices_universe,
            str,
        )
        or not prices_universe
        or prices_universe
        != snapshot_universe
    ):
        raise RuntimeError(
            "legacy_pair_universe_mismatch"
        )

    prices_source = prices.get(
        "source"
    )
    snapshot_source = snapshot.get(
        "source"
    )

    if (
        not isinstance(
            prices_source,
            str,
        )
        or not prices_source
        or prices_source
        != snapshot_source
    ):
        raise RuntimeError(
            "legacy_pair_source_mismatch"
        )

    prices_status = prices.get(
        "status"
    )
    snapshot_status = snapshot.get(
        "status"
    )

    if (
        not isinstance(
            prices_status,
            str,
        )
        or not prices_status
        or prices_status
        != snapshot_status
    ):
        raise RuntimeError(
            "legacy_pair_status_mismatch"
        )

    prices_map = prices.get("prices")
    snapshot_map = snapshot.get(
        "prices"
    )

    if (
        not isinstance(prices_map, dict)
        or not isinstance(
            snapshot_map,
            dict,
        )
        or not prices_map
        or set(prices_map)
        != set(snapshot_map)
    ):
        raise RuntimeError(
            "legacy_pair_symbol_mismatch"
        )

    prices_count = prices.get(
        "symbol_count"
    )
    snapshot_count = snapshot.get(
        "symbol_count"
    )

    if (
        not isinstance(
            prices_count,
            int,
        )
        or isinstance(
            prices_count,
            bool,
        )
        or not isinstance(
            snapshot_count,
            int,
        )
        or isinstance(
            snapshot_count,
            bool,
        )
        or prices_count
        != snapshot_count
        or prices_count
        != len(prices_map)
    ):
        raise RuntimeError(
            "legacy_pair_symbol_count_mismatch"
        )

    return {
        "mode": "LEGACY_V1",
        "generation_id": None,
        "market_session": None,
        "ts": prices_ts,
        "symbol_count": prices_count,
    }


def validate_v2_pair(
    prices: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if (
        prices.get("engine")
        != "offensive_canonical_market_feed_v2"
    ):
        raise RuntimeError(
            "v2_prices_engine_invalid"
        )

    if (
        snapshot.get("engine")
        != "offensive_canonical_snapshot_v2"
    ):
        raise RuntimeError(
            "v2_snapshot_engine_invalid"
        )

    prices_generation = (
        prices.get("generation_id")
    )
    snapshot_generation = (
        snapshot.get("generation_id")
    )

    if (
        not isinstance(
            prices_generation,
            str,
        )
        or not prices_generation
        or not isinstance(
            snapshot_generation,
            str,
        )
        or not snapshot_generation
    ):
        raise RuntimeError(
            "v2_generation_id_missing"
        )

    if (
        prices_generation
        != snapshot_generation
    ):
        raise RuntimeError(
            "v2_generation_id_mismatch"
        )

    prices_session = (
        prices.get("market_session")
    )
    snapshot_session = (
        snapshot.get("market_session")
    )

    if (
        not isinstance(
            prices_session,
            str,
        )
        or not prices_session
        or not isinstance(
            snapshot_session,
            str,
        )
        or not snapshot_session
    ):
        raise RuntimeError(
            "v2_market_session_missing"
        )

    if (
        prices_session
        != snapshot_session
    ):
        raise RuntimeError(
            "v2_market_session_mismatch"
        )

    prices_universe = prices.get(
        "universe"
    )
    snapshot_universe = snapshot.get(
        "universe"
    )

    if (
        not isinstance(
            prices_universe,
            str,
        )
        or not prices_universe
        or not isinstance(
            snapshot_universe,
            str,
        )
        or not snapshot_universe
        or prices_universe
        != snapshot_universe
    ):
        raise RuntimeError(
            "v2_pair_universe_mismatch"
        )

    prices_map = prices.get("prices")
    snapshot_map = snapshot.get("prices")

    if (
        not isinstance(prices_map, dict)
        or not isinstance(
            snapshot_map,
            dict,
        )
        or set(prices_map)
        != set(snapshot_map)
    ):
        raise RuntimeError(
            "v2_pair_symbol_mismatch"
        )

    return {
        "mode": "V2",
        "generation_id": (
            prices_generation
        ),
        "market_session": (
            prices_session
        ),
        "ts": prices.get("ts"),
        "symbol_count": len(
            prices_map
        ),
    }


def validate_reader_admission(
    *,
    active_prices: Path = ACTIVE_PRICES,
    active_snapshot: Path = ACTIVE_SNAPSHOT,
    backup_root: Path = BACKUP_ROOT,
    reference_time: datetime | None = None,
) -> dict[str, Any]:
    assert_no_prepared_transaction(
        backup_root
    )

    if not active_prices.is_file():
        raise RuntimeError(
            "canonical_prices_missing"
        )

    if not active_snapshot.is_file():
        raise RuntimeError(
            "canonical_snapshot_missing"
        )

    prices = read_json(
        active_prices
    )

    snapshot = read_json(
        active_snapshot
    )

    if prices.get("canonical") is not True:
        raise RuntimeError(
            "canonical_prices_flag_invalid"
        )

    if snapshot.get("canonical") is not True:
        raise RuntimeError(
            "canonical_snapshot_flag_invalid"
        )

    prices_generation = (
        prices.get("generation_id")
    )
    snapshot_generation = (
        snapshot.get("generation_id")
    )

    prices_has_generation = bool(
        prices_generation
    )
    snapshot_has_generation = bool(
        snapshot_generation
    )

    # A V1/V2 transition must never be visible
    # to a reader.
    if (
        prices_has_generation
        != snapshot_has_generation
    ):
        raise RuntimeError(
            "canonical_mixed_generation_pair"
        )

    if prices_has_generation:
        result = validate_v2_pair(
            prices,
            snapshot,
        )

        observed_at = (
            reference_time
            if reference_time is not None
            else datetime.now(timezone.utc)
        )

        try:
            expected_market_session = (
                latest_completed_xnys_session(
                    reference_time=observed_at,
                )
            )
        except Exception as exc:
            raise RuntimeError(
                "canonical_xnys_session_authority_unavailable"
            ) from exc

        if (
            result["market_session"]
            != expected_market_session
        ):
            raise RuntimeError(
                "canonical_market_session_stale:"
                f"actual={result['market_session']}:"
                f"expected={expected_market_session}"
            )

        result["expected_market_session"] = (
            expected_market_session
        )
    else:
        # Legacy admission is intentionally strict:
        # both members must be the known canonical V1
        # engines and have no V2 session metadata.
        if (
            prices.get("market_session")
            or snapshot.get(
                "market_session"
            )
        ):
            raise RuntimeError(
                "canonical_mixed_schema_pair"
            )

        result = validate_legacy_pair(
            prices,
            snapshot,
        )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prices",
        type=Path,
        default=ACTIVE_PRICES,
    )

    parser.add_argument(
        "--snapshot",
        type=Path,
        default=ACTIVE_SNAPSHOT,
    )

    parser.add_argument(
        "--backup-root",
        type=Path,
        default=BACKUP_ROOT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    result = validate_reader_admission(
        active_prices=args.prices,
        active_snapshot=args.snapshot,
        backup_root=args.backup_root,
    )

    print("CANONICAL_READER_ADMISSION=PASS")
    print(
        f"CANONICAL_MODE={result['mode']}"
    )
    print(
        "CANONICAL_GENERATION_ID="
        f"{result['generation_id']}"
    )
    print(
        "CANONICAL_MARKET_SESSION="
        f"{result['market_session']}"
    )
    print(
        "CANONICAL_SYMBOL_COUNT="
        f"{result['symbol_count']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
