from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.v2.portfolio.long_term_consolidator import resolve_price_eur


POLICY_PATH = Path(
    "/opt/nsc/app/src/v2/config/offensive_lt_policy.json"
)
REGIME_PATH = Path(
    "/opt/nsc/app/data/equities_offensive/market/market_regime.json"
)
TRANSFERS_PATH = Path(
    "/opt/nsc/data/preprod/portfolio/transfer_instructions.jsonl"
)
POSITIONS_PATH = Path(
    "/opt/nsc/data/preprod/long_term/state/equity_positions.json"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    except Exception as exc:
        raise RuntimeError(
            f"Invalid JSON source {path}: {exc}"
        ) from exc


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        for line in f:
            if line.strip():
                rows.append(
                    json.loads(line)
                )

    return rows


def write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    json.loads(
        tmp.read_text(
            encoding="utf-8"
        )
    )

    tmp.replace(path)


def normalize_regime(
    raw: Any,
) -> str:
    value = str(
        raw or ""
    )

    if value in {
        "risk_on",
        "risk_off",
        "balanced",
    }:
        return value

    return "balanced"


def main() -> dict[str, Any]:
    policy = (
        read_json(
            POLICY_PATH,
            {},
        )
        or {}
    )

    regime_payload = (
        read_json(
            REGIME_PATH,
            {},
        )
        or {}
    )

    transfers = read_jsonl(
        TRANSFERS_PATH
    )

    registry = (
        read_json(
            POSITIONS_PATH,
            {},
        )
        or {}
    )

    positions = registry.get(
        "positions",
        [],
    )

    if not isinstance(
        positions,
        list,
    ):
        raise RuntimeError(
            "Long Term equities positions must be a list"
        )

    processed_transfer_ids = (
        registry.get(
            "processed_transfer_ids",
            [],
        )
    )

    if not isinstance(
        processed_transfer_ids,
        list,
    ):
        raise RuntimeError(
            "processed_transfer_ids must be a list"
        )

    regime = normalize_regime(
        regime_payload.get(
            "regime",
            "balanced",
        )
    )

    regime_weights = (
        (
            policy.get(
                "regimes",
                {},
            )
            or {}
        ).get(
            regime,
            {},
        )
        or {}
    )

    if not isinstance(
        regime_weights,
        dict,
    ) or not regime_weights:
        raise RuntimeError(
            f"No LT policy found for regime={regime}"
        )

    weight_sum = sum(
        float(weight or 0.0)
        for weight in regime_weights.values()
    )

    if abs(
        weight_sum - 1.0
    ) > 0.01:
        raise RuntimeError(
            "LT equity regime weights must sum to 1.0 "
            f"(actual={weight_sum})"
        )

    lt_flows = []

    for row in transfers:
        if row.get("to_pocket") != "lt":
            continue

        if (
            row.get("brick")
            != "equities_offensive"
        ):
            continue

        if str(
            row.get("status") or ""
        ).lower() != "approved":
            continue

        amount_eur = float(
            row.get(
                "amount_eur",
                0.0,
            )
            or 0.0
        )

        if amount_eur <= 0:
            raise RuntimeError(
                "Approved offensive LT transfer "
                "must have amount_eur > 0"
            )

        transfer_id = (
            f'{row.get("brick", "unknown")}'
            f'::{row.get("ts", "")}'
            f'::{amount_eur}'
        )

        if (
            transfer_id
            in processed_transfer_ids
        ):
            continue

        lt_flows.append(
            (
                transfer_id,
                row,
            )
        )

    if not lt_flows:
        result = {
            "status": "ok",
            "engine": "offensive_lt_allocator_v2",
            "message": "no new approved offensive LT flows",
            "regime": regime,
        }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return result

    # Every required market price must resolve
    # successfully BEFORE any position is created.
    live_prices: dict[str, float] = {}

    for symbol in regime_weights:
        resolved = resolve_price_eur(
            symbol,
            "equity",
        )

        price_eur = float(
            resolved.get(
                "price_eur",
                0.0,
            )
            or 0.0
        )

        if price_eur <= 0:
            raise RuntimeError(
                f"Invalid live EUR price for {symbol}"
            )

        if resolved.get("fallback_used"):
            raise RuntimeError(
                f"Synthetic fallback forbidden for {symbol}"
            )

        live_prices[
            symbol
        ] = price_eur

    created = []

    for transfer_id, flow in lt_flows:
        amount_eur = float(
            flow["amount_eur"]
        )

        flow_ts = str(
            flow.get(
                "ts",
                utc_now(),
            )
        )

        safe_ts = (
            flow_ts
            .replace(":", "")
            .replace("-", "")
        )

        for symbol, weight in regime_weights.items():
            invested = round(
                amount_eur
                * float(weight),
                6,
            )

            price_eur = live_prices[
                symbol
            ]

            units = round(
                invested / price_eur,
                12,
            )

            position = {
                "position_id": (
                    "lt_equities_offensive_"
                    f"{symbol}_{safe_ts}"
                ),
                "symbol": symbol,
                "asset_name": symbol,
                "asset_class": "equity",
                "bucket": "equities_lt",
                "source_brick": "equities_offensive",
                "invested_eur": invested,
                "units": units,
                "avg_price_eur": round(
                    price_eur,
                    6,
                ),
                "custody_type": "simulated_broker_account",
                "custody_location": "PREPROD_IBKR_SIMULATED",
                "custody_status": "simulated",
                "status": "SIMULATED",
                "execution_mode": "SIMULATED_ONLY",
                "price_source_required": "live",
            }

            positions.append(
                position
            )

            created.append(
                position
            )

        processed_transfer_ids.append(
            transfer_id
        )

    registry["status"] = "ok"
    registry[
        "engine"
    ] = "long_term_positions_registry_v2"
    registry["environment"] = "PREPROD"
    registry[
        "execution_mode"
    ] = "SIMULATED_ONLY"
    registry["currency"] = "EUR"
    registry["positions"] = positions
    registry[
        "processed_transfer_ids"
    ] = processed_transfer_ids
    registry["updated_at"] = utc_now()

    write_json_atomic(
        POSITIONS_PATH,
        registry,
    )

    result = {
        "status": "ok",
        "engine": "offensive_lt_allocator_v2",
        "environment": "PREPROD",
        "execution_mode": "SIMULATED_ONLY",
        "regime": regime,
        "approved_flows_processed": len(
            lt_flows
        ),
        "created_positions": len(
            created
        ),
        "symbols": sorted(
            regime_weights.keys()
        ),
        "updated_at": registry[
            "updated_at"
        ],
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return result


if __name__ == "__main__":
    main()
