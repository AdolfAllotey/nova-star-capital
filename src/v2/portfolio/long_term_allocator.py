from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.v2.portfolio.long_term_consolidator import resolve_price_eur


TRANSFER_PATH = Path(
    "/opt/nsc/data/preprod/portfolio/transfer_instructions.jsonl"
)
PORTFOLIO_PATH = Path(
    "/opt/nsc/data/preprod/long_term/state/crypto_positions.json"
)

LT_WEIGHTS = {
    "BTC": 0.50,
    "ETH": 0.30,
    "SOL": 0.20,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

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


def read_portfolio() -> dict[str, Any]:
    if not PORTFOLIO_PATH.exists():
        return {
            "status": "ok",
            "engine": "long_term_allocator_v3",
            "environment": "PREPROD",
            "execution_mode": "SIMULATED_ONLY",
            "positions": {},
            "total_value_eur": 0.0,
            "flows_processed": [],
        }

    data = json.loads(
        PORTFOLIO_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            "Long Term crypto portfolio must be a JSON object"
        )

    if "positions" not in data:
        allocation = (
            data.get("allocation", {})
            if isinstance(data.get("allocation"), dict)
            else {}
        )

        weights = (
            data.get("weights", {})
            if isinstance(data.get("weights"), dict)
            else {}
        )

        positions = {}

        for asset, amount in allocation.items():
            positions[str(asset).upper()] = {
                "invested_eur": float(amount or 0.0),
                "units": 0.0,
                "avg_price_eur": 0.0,
                "weight": float(
                    weights.get(asset, 0.0)
                    or 0.0
                ),
            }

        data = {
            "status": "ok",
            "engine": "long_term_allocator_v3",
            "environment": "PREPROD",
            "execution_mode": "SIMULATED_ONLY",
            "positions": positions,
            "total_value_eur": float(
                data.get(
                    "total_lt_capital_eur",
                    0.0,
                )
                or 0.0
            ),
            "flows_processed": [],
        }

    if not isinstance(
        data.get("positions"),
        dict,
    ):
        raise RuntimeError(
            "Long Term crypto positions must be a symbol-keyed object"
        )

    if not isinstance(
        data.get("flows_processed"),
        list,
    ):
        data["flows_processed"] = []

    return data


def save_portfolio(
    data: dict[str, Any],
) -> None:
    data["status"] = "ok"
    data["engine"] = "long_term_allocator_v3"
    data["environment"] = "PREPROD"
    data["execution_mode"] = "SIMULATED_ONLY"
    data["timestamp"] = utc_now()

    write_json_atomic(
        PORTFOLIO_PATH,
        data,
    )


def run() -> dict[str, Any]:
    transfers = read_jsonl(
        TRANSFER_PATH
    )
    portfolio = read_portfolio()

    processed_ids = set(
        portfolio.get(
            "flows_processed",
            [],
        )
    )

    new_flows = [
        row
        for row in transfers
        if row.get("to_pocket") == "lt"
        and str(
            row.get("status") or ""
        ).lower() == "approved"
        and row.get("brick") == "crypto"
        and row.get("ts") not in processed_ids
    ]

    if not new_flows:
        result = {
            "status": "ok",
            "engine": "long_term_allocator_v3",
            "message": "no new approved crypto LT flows",
            "created_or_updated_assets": 0,
        }

        print(
            json.dumps(
                result,
                indent=2,
            )
        )

        return result

    for flow in new_flows:
        amount = float(
            flow.get(
                "amount_eur",
                0.0,
            )
            or 0.0
        )

        if amount <= 0:
            raise RuntimeError(
                "Approved Long Term crypto transfer "
                "must have amount_eur > 0"
            )

    # Resolve every required live price BEFORE
    # mutating any portfolio state.
    prices: dict[str, float] = {}

    for asset in LT_WEIGHTS:
        resolved = resolve_price_eur(
            asset,
            "crypto",
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
                f"Invalid live EUR price for {asset}"
            )

        if resolved.get("fallback_used"):
            raise RuntimeError(
                f"Synthetic fallback forbidden for {asset}"
            )

        prices[asset] = price_eur

    positions = portfolio["positions"]

    total_added = 0.0

    for flow in new_flows:
        amount_eur = float(
            flow["amount_eur"]
        )

        for asset, weight in LT_WEIGHTS.items():
            allocated_eur = (
                amount_eur
                * float(weight)
            )

            price_eur = prices[asset]

            added_units = (
                allocated_eur
                / price_eur
            )

            current = positions.get(
                asset,
                {},
            )

            if not isinstance(
                current,
                dict,
            ):
                raise RuntimeError(
                    f"Invalid existing LT position for {asset}"
                )

            previous_invested = float(
                current.get(
                    "invested_eur",
                    current.get(
                        "amount_eur",
                        0.0,
                    ),
                )
                or 0.0
            )

            previous_units = float(
                current.get(
                    "units",
                    0.0,
                )
                or 0.0
            )

            new_invested = (
                previous_invested
                + allocated_eur
            )

            new_units = (
                previous_units
                + added_units
            )

            avg_price_eur = (
                new_invested
                / new_units
                if new_units > 0
                else 0.0
            )

            positions[asset] = {
                "invested_eur": round(
                    new_invested,
                    6,
                ),
                "units": round(
                    new_units,
                    12,
                ),
                "avg_price_eur": round(
                    avg_price_eur,
                    6,
                ),
                "weight": 0.0,
                "last_allocation_price_eur": round(
                    price_eur,
                    6,
                ),
                "price_source_required": "live",
            }

        portfolio[
            "flows_processed"
        ].append(
            flow.get("ts")
        )

        total_added += amount_eur

    total_invested = sum(
        float(
            payload.get(
                "invested_eur",
                0.0,
            )
            or 0.0
        )
        for payload in positions.values()
        if isinstance(
            payload,
            dict,
        )
    )

    portfolio[
        "total_value_eur"
    ] = round(
        total_invested,
        6,
    )

    for payload in positions.values():
        invested = float(
            payload.get(
                "invested_eur",
                0.0,
            )
            or 0.0
        )

        payload["weight"] = round(
            invested / total_invested,
            6,
        ) if total_invested > 0 else 0.0

    save_portfolio(
        portfolio
    )

    result = {
        "status": "updated",
        "engine": "long_term_allocator_v3",
        "environment": "PREPROD",
        "execution_mode": "SIMULATED_ONLY",
        "approved_flows_processed": len(
            new_flows
        ),
        "added_eur": round(
            total_added,
            2,
        ),
        "total_lt_invested_eur": round(
            total_invested,
            2,
        ),
        "positions": positions,
    }

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    return result


if __name__ == "__main__":
    run()
