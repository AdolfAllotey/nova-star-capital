from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.v2.portfolio.capital_flow_engine import (
    compute_profit_flow,
    get_applicable_tier,
    load_policy,
)


DATA_DIR = Path(
    os.environ.get(
        "NSC_DATA_DIR",
        "/opt/nsc/data/preprod",
    )
)

RC2_POLICY_PATH = Path(
    "/opt/nsc/app/src/v2/config/"
    "waterfall_rc2_policy.json"
)

WATERFALL_DIR = DATA_DIR / "portfolio" / "waterfall"

STATE_PATH = WATERFALL_DIR / "waterfall_state.json"
EVENTS_PATH = WATERFALL_DIR / "waterfall_events.jsonl"
INSTRUCTIONS_PATH = (
    WATERFALL_DIR / "distribution_instructions.jsonl"
)
SUMMARY_PATH = WATERFALL_DIR / "waterfall_summary.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(
    path: Path,
    default: Any = None,
) -> Any:
    try:
        if path.exists():
            return json.loads(
                path.read_text(encoding="utf-8")
            )
    except Exception:
        pass

    return default


def atomic_write_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_name(
        f".{path.name}.tmp"
    )

    tmp.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(tmp, path)


def append_jsonl(
    path: Path,
    payload: Dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                payload,
                ensure_ascii=False,
            )
            + "\n"
        )


def load_rc2_policy() -> Dict[str, Any]:
    payload = read_json(
        RC2_POLICY_PATH,
        {},
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            "Invalid RC2 waterfall policy"
        )

    return payload


def current_tier(
    capital_eur: float,
) -> Dict[str, Any]:
    policy = load_policy()

    tier = get_applicable_tier(
        capital_eur,
        policy["tiers"],
    )

    return {
        "min_capital_eur": float(
            tier["min_capital_eur"]
        ),
        "trading": float(
            tier["trading"]
        ),
        "distribution": float(
            tier["distribution"]
        ),
    }


def read_crypto_source(
    path: Path,
) -> Tuple[float, str, str]:
    data = read_json(
        path,
        {},
    )

    summary = (
        data.get("summary")
        if isinstance(data, dict)
        else {}
    ) or {}

    realized = float(
        summary.get(
            "realized_pnl_eur",
            0.0,
        )
        or 0.0
    )

    timestamp = str(
        data.get("updated_at")
        or ""
    )

    return (
        realized,
        "EUR",
        timestamp,
    )


def read_offensive_source(
    path: Path,
) -> Tuple[float, str, str]:
    data = read_json(
        path,
        {},
    )

    summary = (
        data.get("summary")
        if isinstance(data, dict)
        else {}
    ) or {}

    realized = float(
        summary.get(
            "realized_pnl_usd",
            0.0,
        )
        or 0.0
    )

    currency = str(
        data.get("currency")
        or "USD"
    ).upper()

    timestamp = str(
        data.get("ts")
        or ""
    )

    return (
        realized,
        currency,
        timestamp,
    )


def read_realized_source(
    brick: str,
    path: Path,
) -> Tuple[float, str, str]:
    if brick == "crypto":
        return read_crypto_source(path)

    if brick == "equities_offensive":
        return read_offensive_source(path)

    raise RuntimeError(
        f"Unsupported waterfall brick: {brick}"
    )


def event_id(
    brick: str,
    source_timestamp: str,
    realized_native: float,
) -> str:
    raw = (
        f"{brick}|"
        f"{source_timestamp}|"
        f"{realized_native:.8f}"
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]

    return f"wf_{brick}_{digest}"


def build_initial_brick_state(
    brick: str,
    cfg: Dict[str, Any],
    realized_native: float,
    currency: str,
    source_timestamp: str,
) -> Dict[str, Any]:
    seed = float(
        cfg.get(
            "seed_waterfall_capital_eur",
            0.0,
        )
        or 0.0
    )

    return {
        "brick": brick,
        "enabled": bool(
            cfg.get(
                "enabled",
                False,
            )
        ),
        "source_pool": cfg.get(
            "source_pool"
        ),
        "seed_waterfall_capital_eur": round(
            seed,
            2,
        ),
        "waterfall_capital_eur": round(
            seed,
            2,
        ),
        "last_processed_realized_pnl_native": round(
            realized_native,
            8,
        ),
        "source_currency": currency,
        "last_source_timestamp": source_timestamp,
        "cumulative_positive_delta_eur": 0.0,
        "cumulative_negative_delta_eur": 0.0,
        "cumulative_tax_eur": 0.0,
        "cumulative_reinvested_eur": 0.0,
        "cumulative_distributed_eur": {
            "lt": 0.0,
            "bfr": 0.0,
            "security": 0.0,
        },
        "tier": current_tier(seed),
        "status": "BOOTSTRAPPED",
    }


def bootstrap_state(
    write: bool,
) -> Dict[str, Any]:
    policy = load_rc2_policy()

    bricks_cfg = (
        policy.get("alpha_bricks")
        or {}
    )

    bricks: Dict[str, Any] = {}

    for brick, cfg in bricks_cfg.items():
        source_path = Path(
            str(
                cfg.get(
                    "realized_pnl_source"
                )
            )
        )

        realized, currency, timestamp = (
            read_realized_source(
                brick,
                source_path,
            )
        )

        bricks[brick] = (
            build_initial_brick_state(
                brick,
                cfg,
                realized,
                currency,
                timestamp,
            )
        )

    payload = {
        "status": "ok",
        "engine": "waterfall_runtime_v1",
        "mode": "SIMULATED_ONLY",
        "bootstrapped_at": utc_now(),
        "updated_at": utc_now(),
        "bricks": bricks,
        "safety": policy.get(
            "safety",
            {},
        ),
    }

    if write:
        atomic_write_json(
            STATE_PATH,
            payload,
        )

    return payload


def native_delta_to_eur(
    brick: str,
    delta: float,
    currency: str,
) -> Tuple[Optional[float], str]:
    if currency == "EUR":
        return delta, "identity"

    # RC2 fail-closed:
    # equities offensive ledger is currently USD.
    # No arbitrary FX approximation is allowed.
    if currency == "USD":
        return (
            None,
            "canonical_usd_eur_fx_required",
        )

    return (
        None,
        f"unsupported_currency:{currency}",
    )


def create_instruction(
    *,
    event: str,
    brick: str,
    source_pool: str,
    destination: str,
    amount_eur: float,
    instruction_type: str,
    safety: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "instruction_id": (
            f"{event}_{instruction_type}_"
            f"{destination}"
        ),
        "timestamp": utc_now(),
        "engine": "waterfall_runtime_v1",
        "brick": brick,
        "from_pool": source_pool,
        "to_pocket": destination,
        "amount_eur": round(
            amount_eur,
            6,
        ),
        "instruction_type": instruction_type,
        "status": "simulated_pending_review",
        "execution_mode": "SIMULATED_ONLY",
        "execution_allowed": False,
        "real_money_enabled": False,
        "automatic_transfer_allowed": False,
        "transfer_mode": safety.get(
            "transfer_mode",
            "simulated_manual_review",
        ),
        "manual_review_required": True,
    }


def process_brick(
    *,
    brick: str,
    cfg: Dict[str, Any],
    state_row: Dict[str, Any],
    safety: Dict[str, Any],
    write: bool,
) -> Dict[str, Any]:
    source_path = Path(
        str(
            cfg.get(
                "realized_pnl_source"
            )
        )
    )

    current_native, currency, source_ts = (
        read_realized_source(
            brick,
            source_path,
        )
    )

    previous_native = float(
        state_row.get(
            "last_processed_realized_pnl_native",
            0.0,
        )
        or 0.0
    )

    delta_native = (
        current_native
        - previous_native
    )

    delta_eur, conversion = (
        native_delta_to_eur(
            brick,
            delta_native,
            currency,
        )
    )

    base_result = {
        "brick": brick,
        "source": str(source_path),
        "source_timestamp": source_ts,
        "source_currency": currency,
        "previous_realized_pnl_native": round(
            previous_native,
            8,
        ),
        "current_realized_pnl_native": round(
            current_native,
            8,
        ),
        "delta_realized_pnl_native": round(
            delta_native,
            8,
        ),
        "conversion": conversion,
    }

    if abs(delta_native) < 1e-12:
        state_row["last_source_timestamp"] = (
            source_ts
        )
        state_row["status"] = (
            "NO_NEW_REALIZED_PNL"
        )

        return {
            **base_result,
            "status": "no_change",
        }

    if delta_eur is None:
        state_row["status"] = (
            "BLOCKED_MISSING_CANONICAL_FX"
        )

        return {
            **base_result,
            "status": "blocked",
            "reason": conversion,
        }

    event = event_id(
        brick,
        source_ts,
        current_native,
    )

    pre_capital = float(
        state_row.get(
            "waterfall_capital_eur",
            0.0,
        )
        or 0.0
    )

    instructions = []

    if delta_eur < 0:
        post_capital = max(
            0.0,
            pre_capital + delta_eur,
        )

        state_row[
            "waterfall_capital_eur"
        ] = round(
            post_capital,
            2,
        )

        state_row[
            "cumulative_negative_delta_eur"
        ] = round(
            float(
                state_row.get(
                    "cumulative_negative_delta_eur",
                    0.0,
                )
                or 0.0
            )
            + abs(delta_eur),
            2,
        )

        flow = {
            "brick": brick,
            "input_profit": delta_eur,
            "tax": 0.0,
            "net_profit": 0.0,
            "trading_reinvested": 0.0,
            "distributed": {
                "lt": 0.0,
                "bfr": 0.0,
                "security": 0.0,
            },
        }

        event_type = (
            "REALIZED_LOSS_APPLIED"
        )

    else:
        flow = compute_profit_flow(
            brick=brick,
            profit_eur=delta_eur,
            capital_eur=pre_capital,
        )

        reinvested = float(
            flow.get(
                "trading_reinvested",
                0.0,
            )
            or 0.0
        )

        post_capital = (
            pre_capital
            + reinvested
        )

        state_row[
            "waterfall_capital_eur"
        ] = round(
            post_capital,
            2,
        )

        state_row[
            "cumulative_positive_delta_eur"
        ] = round(
            float(
                state_row.get(
                    "cumulative_positive_delta_eur",
                    0.0,
                )
                or 0.0
            )
            + delta_eur,
            2,
        )

        tax = float(
            flow.get("tax", 0.0)
            or 0.0
        )

        state_row[
            "cumulative_tax_eur"
        ] = round(
            float(
                state_row.get(
                    "cumulative_tax_eur",
                    0.0,
                )
                or 0.0
            )
            + tax,
            2,
        )

        state_row[
            "cumulative_reinvested_eur"
        ] = round(
            float(
                state_row.get(
                    "cumulative_reinvested_eur",
                    0.0,
                )
                or 0.0
            )
            + reinvested,
            2,
        )

        if tax > 0:
            instructions.append(
                create_instruction(
                    event=event,
                    brick=brick,
                    source_pool=cfg.get(
                        "source_pool",
                        "unknown_pool",
                    ),
                    destination="tax_reserve",
                    amount_eur=tax,
                    instruction_type=(
                        "tax_reserve"
                    ),
                    safety=safety,
                )
            )

        distributed = (
            flow.get("distributed")
            or {}
        )

        cumulative_dist = (
            state_row.get(
                "cumulative_distributed_eur"
            )
            or {}
        )

        for pocket in (
            "lt",
            "bfr",
            "security",
        ):
            amount = float(
                distributed.get(
                    pocket,
                    0.0,
                )
                or 0.0
            )

            cumulative_dist[pocket] = round(
                float(
                    cumulative_dist.get(
                        pocket,
                        0.0,
                    )
                    or 0.0
                )
                + amount,
                2,
            )

            if amount > 0:
                instructions.append(
                    create_instruction(
                        event=event,
                        brick=brick,
                        source_pool=cfg.get(
                            "source_pool",
                            "unknown_pool",
                        ),
                        destination=pocket,
                        amount_eur=amount,
                        instruction_type=(
                            "profit_distribution"
                        ),
                        safety=safety,
                    )
                )

        state_row[
            "cumulative_distributed_eur"
        ] = cumulative_dist

        event_type = (
            "REALIZED_PROFIT_PROCESSED"
        )

    state_row[
        "last_processed_realized_pnl_native"
    ] = round(
        current_native,
        8,
    )

    state_row[
        "last_source_timestamp"
    ] = source_ts

    state_row["tier"] = current_tier(
        float(
            state_row.get(
                "waterfall_capital_eur",
                0.0,
            )
            or 0.0
        )
    )

    state_row["status"] = "ACTIVE"

    event_payload = {
        "event_id": event,
        "timestamp": utc_now(),
        "engine": "waterfall_runtime_v1",
        "type": event_type,
        "brick": brick,
        "source_pool": cfg.get(
            "source_pool"
        ),
        "source_timestamp": source_ts,
        "source_currency": currency,
        "delta_realized_pnl_eur": round(
            delta_eur,
            6,
        ),
        "capital_before_eur": round(
            pre_capital,
            2,
        ),
        "capital_after_eur": round(
            float(
                state_row[
                    "waterfall_capital_eur"
                ]
            ),
            2,
        ),
        "flow": flow,
        "tier_after": state_row["tier"],
        "execution_mode": "SIMULATED_ONLY",
        "execution_allowed": False,
        "real_money_enabled": False,
    }

    if write:
        append_jsonl(
            EVENTS_PATH,
            event_payload,
        )

        for instruction in instructions:
            append_jsonl(
                INSTRUCTIONS_PATH,
                instruction,
            )

    return {
        **base_result,
        "status": "processed",
        "event_id": event,
        "flow": flow,
        "capital_before_eur": round(
            pre_capital,
            2,
        ),
        "capital_after_eur": round(
            float(
                state_row[
                    "waterfall_capital_eur"
                ]
            ),
            2,
        ),
        "instructions_count": len(
            instructions
        ),
    }


def run_runtime(
    write: bool,
) -> Dict[str, Any]:
    policy = load_rc2_policy()

    state = read_json(
        STATE_PATH,
        None,
    )

    if not isinstance(state, dict):
        return {
            "status": "bootstrap_required",
            "engine": "waterfall_runtime_v1",
            "state_path": str(
                STATE_PATH
            ),
        }

    bricks_cfg = (
        policy.get("alpha_bricks")
        or {}
    )

    safety = (
        policy.get("safety")
        or {}
    )

    results = []

    state_bricks = (
        state.get("bricks")
        or {}
    )

    for brick, cfg in bricks_cfg.items():
        if not cfg.get(
            "enabled",
            False,
        ):
            continue

        row = state_bricks.get(brick)

        if not isinstance(row, dict):
            raise RuntimeError(
                f"Missing state for {brick}"
            )

        results.append(
            process_brick(
                brick=brick,
                cfg=cfg,
                state_row=row,
                safety=safety,
                write=write,
            )
        )

    state["updated_at"] = utc_now()
    state["bricks"] = state_bricks

    summary = {
        "status": "ok",
        "engine": "waterfall_runtime_v1",
        "generated_at": utc_now(),
        "mode": "SIMULATED_ONLY",
        "execution_allowed": False,
        "real_money_enabled": False,
        "automatic_transfer_allowed": False,
        "results": results,
        "bricks": {
            brick: {
                "waterfall_capital_eur": (
                    row.get(
                        "waterfall_capital_eur"
                    )
                ),
                "tier": row.get("tier"),
                "status": row.get(
                    "status"
                ),
            }
            for brick, row
            in state_bricks.items()
        },
    }

    if write:
        atomic_write_json(
            STATE_PATH,
            state,
        )

        atomic_write_json(
            SUMMARY_PATH,
            summary,
        )

    return summary


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--bootstrap",
        action="store_true",
    )

    parser.add_argument(
        "--write",
        action="store_true",
    )

    args = parser.parse_args()

    if args.bootstrap:
        payload = bootstrap_state(
            write=args.write,
        )
    else:
        payload = run_runtime(
            write=args.write,
        )

    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
