#!/usr/bin/env python3

import hashlib
import math
from typing import Any


SCHEMA_VERSION = 1
ENGINE = "options_v3_autonomous_shadow"
MODE = "SHADOW"
ENVIRONMENT = "PREPROD"
ACTION_POLICY = "SIMULATED_ONLY"


def _position_ids(positions: list) -> set[str]:
    if not isinstance(positions, list):
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "positions must be a list"
        )

    result = set()

    for position in positions:
        if not isinstance(position, dict):
            continue

        position_id = str(
            position.get("position_id") or ""
        ).strip()

        if not position_id:
            raise RuntimeError(
                "options_v3_cycle_ledger: "
                "position_id required"
            )

        result.add(position_id)

    return result


def _cycle_id(observed_at: str) -> str:
    raw = (
        f"{ENGINE}|{ENVIRONMENT}|{observed_at}"
    )
    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def build_cycle_ledger_entry_v3(
    *,
    observed_at: str,
    pipeline_status: str,
    opportunity_status: str,
    infrastructure_failure_count: int,
    signals_total: int,
    candidates_raw: int,
    candidates_validated: int,
    decisions_total: int,
    approved_count: int,
    rejected_count: int,
    valuation_status: str,
    valued_position_count: int,
    valuation_failure_count: int,
    open_positions_before: list,
    closed_positions_before: list,
    open_positions_after: list,
    closed_positions_after: list,
    existing_used_risk_eur: float,
    new_allocated_risk_eur: float,
    final_open_risk_eur: float,
    used_risk_pct: float,
    available_risk_eur_after_new: float,
    risk_free_rate_provenance: dict,
) -> dict[str, Any]:
    if not isinstance(observed_at, str) or not observed_at:
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "observed_at required"
        )

    if not isinstance(risk_free_rate_provenance, dict):
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "risk_free_rate_provenance required"
        )

    risk_free_provider = str(
        risk_free_rate_provenance.get("provider") or ""
    ).strip()
    risk_free_series_id = str(
        risk_free_rate_provenance.get("series_id") or ""
    ).strip()
    risk_free_observation_date = str(
        risk_free_rate_provenance.get(
            "observation_date"
        )
        or ""
    ).strip()

    if not risk_free_provider:
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "risk-free provider required"
        )

    if not risk_free_series_id:
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "risk-free series_id required"
        )

    if not risk_free_observation_date:
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "risk-free observation_date required"
        )

    try:
        certified_risk_free_rate = float(
            risk_free_rate_provenance[
                "risk_free_rate"
            ]
        )
        risk_free_age_days = int(
            risk_free_rate_provenance["age_days"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "invalid risk-free numeric contract"
        ) from exc

    if not math.isfinite(certified_risk_free_rate):
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "risk-free rate must be finite"
        )

    if risk_free_age_days < 0:
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "risk-free age_days invalid"
        )

    if (
        risk_free_rate_provenance.get(
            "freshness_verified"
        )
        is not True
    ):
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "risk-free freshness not verified"
        )

    open_before_ids = _position_ids(
        open_positions_before
    )
    closed_before_ids = _position_ids(
        closed_positions_before
    )
    open_after_ids = _position_ids(
        open_positions_after
    )
    closed_after_ids = _position_ids(
        closed_positions_after
    )

    opened_ids = sorted(
        open_after_ids
        - open_before_ids
    )

    closed_ids = sorted(
        closed_after_ids
        - closed_before_ids
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "cycle_id": _cycle_id(observed_at),
        "observed_at": observed_at,
        "engine": ENGINE,
        "mode": MODE,
        "environment": ENVIRONMENT,
        "health": {
            "pipeline_status": pipeline_status,
            "opportunity_status": opportunity_status,
            "infrastructure_failure_count": int(
                infrastructure_failure_count
            ),
        },
        "discovery": {
            "signals_total": int(signals_total),
            "candidates_raw": int(candidates_raw),
            "candidates_validated": int(
                candidates_validated
            ),
            "decisions_total": int(
                decisions_total
            ),
            "approved_count": int(approved_count),
            "rejected_count": int(rejected_count),
        },
        "valuation": {
            "status": valuation_status,
            "valued_position_count": int(
                valued_position_count
            ),
            "failure_count": int(
                valuation_failure_count
            ),
            "market_quote_age_verified": False,
        },
        "inventory": {
            "open_count": len(open_after_ids),
            "closed_total_count": len(
                closed_after_ids
            ),
            "opened_position_ids_this_cycle":
                opened_ids,
            "closed_position_ids_this_cycle":
                closed_ids,
        },
        "risk": {
            "existing_used_risk_eur": round(
                float(existing_used_risk_eur),
                2,
            ),
            "new_allocated_risk_eur": round(
                float(new_allocated_risk_eur),
                2,
            ),
            "final_open_risk_eur": round(
                float(final_open_risk_eur),
                2,
            ),
            "used_risk_pct": round(
                float(used_risk_pct),
                8,
            ),
            "available_risk_eur_after_new": round(
                float(
                    available_risk_eur_after_new
                ),
                2,
            ),
        },
        "risk_free_rate": {
            "provider": risk_free_provider,
            "series_id": risk_free_series_id,
            "observation_date":
                risk_free_observation_date,
            "risk_free_rate": round(
                certified_risk_free_rate,
                12,
            ),
            "age_days": risk_free_age_days,
            "freshness_verified": True,
        },
        "execution": {
            "action_policy": ACTION_POLICY,
            "real_execution_allowed": False,
        },
    }


def append_cycle_ledger_entry_v3(
    ledger_path,
    entry: dict,
) -> bool:
    """
    Append one cycle observation exactly once.

    Returns True when appended and False when the same
    cycle_id already exists.

    Existing malformed ledger content fails closed.
    """
    import json
    from pathlib import Path

    path = Path(ledger_path)

    if not isinstance(entry, dict):
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "entry must be a dict"
        )

    cycle_id = str(
        entry.get("cycle_id") or ""
    ).strip()

    if not cycle_id:
        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "cycle_id required"
        )

    seen = set()
    existing_by_cycle_id = {}

    if path.exists():
        try:
            lines = path.read_text().splitlines()
        except Exception as exc:
            raise RuntimeError(
                "options_v3_cycle_ledger: "
                "existing ledger unreadable"
            ) from exc

        for line_number, raw in enumerate(
            lines,
            start=1,
        ):
            if not raw.strip():
                continue

            try:
                existing = json.loads(raw)
            except Exception as exc:
                raise RuntimeError(
                    "options_v3_cycle_ledger: "
                    "malformed existing ledger line "
                    f"{line_number}"
                ) from exc

            if not isinstance(existing, dict):
                raise RuntimeError(
                    "options_v3_cycle_ledger: "
                    "existing ledger entry must be dict"
                )

            existing_cycle_id = str(
                existing.get("cycle_id") or ""
            ).strip()

            if not existing_cycle_id:
                raise RuntimeError(
                    "options_v3_cycle_ledger: "
                    "existing cycle_id required"
                )

            if existing_cycle_id in seen:
                raise RuntimeError(
                    "options_v3_cycle_ledger: "
                    "duplicate existing cycle_id"
                )

            seen.add(existing_cycle_id)
            existing_by_cycle_id[
                existing_cycle_id
            ] = existing

    if cycle_id in seen:
        if existing_by_cycle_id[cycle_id] == entry:
            return False

        raise RuntimeError(
            "options_v3_cycle_ledger: "
            "cycle_id collision with different payload"
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = json.dumps(
        entry,
        sort_keys=True,
        separators=(",", ":"),
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(serialized)
        handle.write("\n")

    return True
