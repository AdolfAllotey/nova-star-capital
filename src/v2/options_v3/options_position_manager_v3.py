from options_data_adapter_v3 import (
    OptionsDataAdapterError,
    adapt_assignment_input_v3,
    adapt_expiration_input_v3,
)
from options_expiration_policy_v3 import evaluate_pre_expiry_close_v3
from options_assignment_guard_v3 import evaluate_assignment_risk_v3

#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/opt/nsc/data/preprod/options_v3")

MAX_DAYS = 45

PNL_STATUS_UNAVAILABLE = "UNAVAILABLE_NO_CERTIFIED_MARKET_VALUATION"
PNL_PROVENANCE_STATUS = "NO_CERTIFIED_OPTION_MARK_PROVENANCE"

def evaluate_position_capabilities_v3(
    position: dict,
    valuation_timestamp=None,
) -> dict:
    enriched = dict(position)

    try:
        expiration_input = adapt_expiration_input_v3(
            enriched,
            valuation_timestamp=valuation_timestamp,
        )

        expiry_decision = evaluate_pre_expiry_close_v3(
            expiration=expiration_input.expiration,
            current_timestamp=(
                expiration_input.valuation_timestamp
            ),
            position_status=str(
                enriched.get("status") or "OPEN"
            ),
            pnl_pct=enriched.get("pnl_pct"),
        )

        assignment_input = adapt_assignment_input_v3(
            enriched,
            valuation_timestamp=valuation_timestamp,
        )

        assignment_decision = evaluate_assignment_risk_v3(
            option_type=assignment_input.option_type,
            strategy=str(
                enriched.get("strategy") or ""
            ),
            days_to_expiry=int(
                assignment_input.days_to_expiry
            ),
            moneyness=assignment_input.moneyness,
            position_status=str(
                enriched.get("status") or "OPEN"
            ),
        )

        if hasattr(expiry_decision, "to_dict"):
            expiry_payload = expiry_decision.to_dict()
        elif hasattr(expiry_decision, "__dict__"):
            expiry_payload = dict(expiry_decision.__dict__)
        elif isinstance(expiry_decision, dict):
            expiry_payload = dict(expiry_decision)
        else:
            expiry_payload = {"decision": str(expiry_decision)}

        if hasattr(assignment_decision, "to_dict"):
            assignment_payload = assignment_decision.to_dict()
        elif hasattr(assignment_decision, "__dict__"):
            assignment_payload = dict(assignment_decision.__dict__)
        elif isinstance(assignment_decision, dict):
            assignment_payload = dict(assignment_decision)
        else:
            assignment_payload = {"decision": str(assignment_decision)}

        enriched["expiration_policy"] = expiry_payload
        enriched["assignment_risk"] = assignment_payload
        enriched["days_to_expiry"] = (
            expiration_input.days_to_expiry
        )
        enriched["expiration"] = expiration_input.expiration
        enriched["capability_adapter_version"] = "options_v3_adapter_v1"
        enriched["execution_mode"] = "SIMULATED_ONLY"
        enriched["real_execution_allowed"] = False

        force_close = bool(
            expiry_payload.get("force_close")
            or expiry_payload.get("should_close")
            or assignment_payload.get("force_close")
            or assignment_payload.get("should_close")
        )

        enriched["capability_lifecycle_action"] = (
            "SIMULATED_CLOSE_REVIEW"
            if force_close
            else "HOLD"
        )
        return enriched

    except OptionsDataAdapterError as exc:
        enriched["capability_lifecycle_action"] = (
            "SIMULATED_CLOSE_REVIEW"
        )
        enriched["capability_rejection_reason"] = str(exc)
        enriched["execution_mode"] = "SIMULATED_ONLY"
        enriched["real_execution_allowed"] = False
        return enriched


def now():
    return datetime.now(timezone.utc)

def load(name, default):
    p = BASE / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default

def save(name, data):
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / name).write_text(json.dumps(data, indent=2))

def _canonical_contract_legs(position: dict) -> list[dict]:
    legs = position.get("contract_legs")

    if not isinstance(legs, list) or not legs:
        raise RuntimeError(
            "options_v3_position_identity: contract_legs required"
        )

    canonical = []

    for leg in legs:
        if not isinstance(leg, dict):
            raise RuntimeError(
                "options_v3_position_identity: invalid contract leg"
            )

        contract_symbol = str(
            leg.get("contract_symbol") or ""
        ).strip()
        side = str(
            leg.get("side") or ""
        ).strip().upper()

        if not contract_symbol or side not in {"BUY", "SELL"}:
            raise RuntimeError(
                "options_v3_position_identity: "
                "contract_symbol and BUY/SELL side required"
            )

        canonical.append(
            {
                "contract_symbol": contract_symbol,
                "side": side,
                "option_type": str(
                    leg.get("option_type") or ""
                ).strip().upper(),
                "strike": leg.get("strike"),
            }
        )

    canonical.sort(
        key=lambda item: (
            item["contract_symbol"],
            item["side"],
            item["option_type"],
            str(item["strike"]),
        )
    )

    return canonical


def build_structure_id_v3(position: dict) -> str:
    ticker = str(
        position.get("ticker") or ""
    ).strip().upper()
    strategy = str(
        position.get("strategy") or ""
    ).strip()
    expiration = str(
        position.get("expiration") or ""
    ).strip()

    if not ticker or not strategy or not expiration:
        raise RuntimeError(
            "options_v3_position_identity: "
            "ticker, strategy and expiration required"
        )

    identity = {
        "ticker": ticker,
        "strategy": strategy,
        "expiration": expiration,
        "contract_legs": _canonical_contract_legs(position),
    }

    raw = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:24]

    return f"optv3_struct_{digest}"


def build_position_id_v3(
    structure_id: str,
    opened_at: str,
) -> str:
    raw = f"{structure_id}|{opened_at}"

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:24]

    return f"optv3_pos_{digest}"


def _prepare_existing_position_v3(position: dict) -> dict:
    pos = dict(position)

    structure_id = pos.get("structure_id")

    if not structure_id:
        structure_id = build_structure_id_v3(pos)
        pos["structure_id"] = structure_id

    opened_at = str(
        pos.get("opened_at") or ""
    ).strip()

    if not opened_at:
        raise RuntimeError(
            "options_v3_position_identity: opened_at required"
        )

    if not pos.get("position_id"):
        pos["position_id"] = build_position_id_v3(
            structure_id,
            opened_at,
        )

    return pos


def _build_new_position_v3(selected: dict) -> dict:
    # Preserve the complete selected trade snapshot so the canonical
    # position retains contract identity, sizing and provenance.
    pos = dict(selected)

    opened_at = now().isoformat()
    structure_id = build_structure_id_v3(pos)

    pos["structure_id"] = structure_id
    pos["position_id"] = build_position_id_v3(
        structure_id,
        opened_at,
    )
    pos["opened_at"] = opened_at
    pos["entry_risk_eur"] = selected.get(
        "allocated_risk_eur",
        selected.get("estimated_risk_eur", 0),
    )
    pos["status"] = "OPEN"
    pos["source"] = "options_v3_portfolio_selected"

    return pos


def _append_closed_unique_v3(
    previously_closed: list,
    newly_closed: list,
) -> list:
    result = []
    seen = set()

    for position in previously_closed + newly_closed:
        if not isinstance(position, dict):
            continue

        position_id = position.get("position_id")

        if not position_id:
            raise RuntimeError(
                "options_v3_closed_history: position_id required"
            )

        if position_id in seen:
            continue

        seen.add(position_id)
        result.append(position)

    return result


def update_positions():
    portfolio = load(
        "options_v3_portfolio_selected.json",
        [],
    )
    existing_raw = load(
        "options_v3_positions.json",
        [],
    )
    previously_closed = load(
        "options_v3_positions_closed.json",
        [],
    )

    if not isinstance(portfolio, list):
        raise RuntimeError(
            "options_v3_portfolio_selected must be a list"
        )

    if not isinstance(existing_raw, list):
        raise RuntimeError(
            "options_v3_positions must be a list"
        )

    if not isinstance(previously_closed, list):
        raise RuntimeError(
            "options_v3_positions_closed must be a list"
        )

    existing = [
        _prepare_existing_position_v3(p)
        for p in existing_raw
        if isinstance(p, dict)
    ]

    existing_map = {
        p["structure_id"]: p
        for p in existing
    }

    selected_map = {}

    for selected in portfolio:
        if not isinstance(selected, dict):
            continue

        structure_id = build_structure_id_v3(selected)

        if structure_id in selected_map:
            # Same exact contract structure in one allocation run:
            # one canonical opening only.
            continue

        selected_map[structure_id] = selected

    # Start from the persistent inventory. Current-run selection is only
    # a source of NEW openings or fresh capability context; it is never
    # the source of truth for whether an existing position still exists.
    inventory = list(existing)

    for structure_id, selected in selected_map.items():
        if structure_id not in existing_map:
            pos = _build_new_position_v3(selected)
            inventory.append(pos)
            existing_map[structure_id] = pos

    open_positions = []
    newly_closed = []

    for stored_position in inventory:
        pos = dict(stored_position)

        selected = selected_map.get(
            pos["structure_id"]
        )

        lifecycle_input = dict(pos)

        if selected is not None:
            # Fresh context may enrich lifecycle evaluation, but immutable
            # opening identity/state remains owned by the inventory.
            lifecycle_input.update(selected)
            lifecycle_input["position_id"] = pos["position_id"]
            lifecycle_input["structure_id"] = pos["structure_id"]
            lifecycle_input["opened_at"] = pos["opened_at"]
            lifecycle_input["entry_risk_eur"] = pos.get(
                "entry_risk_eur",
                0,
            )

        # RC2 valuation contract:
        # no synthetic PnL is permitted.
        lifecycle_input["pnl_eur"] = None
        lifecycle_input["pnl_pct"] = None
        lifecycle_input["pnl_status"] = PNL_STATUS_UNAVAILABLE
        lifecycle_input[
            "pnl_provenance_status"
        ] = PNL_PROVENANCE_STATUS

        evaluated = evaluate_position_capabilities_v3(
            lifecycle_input
        )

        pos.update(evaluated)

        # Preserve immutable inventory identity/opening state.
        pos["position_id"] = stored_position["position_id"]
        pos["structure_id"] = stored_position["structure_id"]
        pos["opened_at"] = stored_position["opened_at"]
        pos["entry_risk_eur"] = stored_position.get(
            "entry_risk_eur",
            0,
        )

        # Capability enrichment must never reintroduce synthetic
        # valuation.
        pos["pnl_eur"] = None
        pos["pnl_pct"] = None
        pos["pnl_status"] = PNL_STATUS_UNAVAILABLE
        pos[
            "pnl_provenance_status"
        ] = PNL_PROVENANCE_STATUS

        opened_at = datetime.fromisoformat(
            pos["opened_at"]
        )
        days = (now() - opened_at).days
        pos["days_in_trade"] = days

        if (
            pos.get("capability_lifecycle_action")
            == "SIMULATED_CLOSE_REVIEW"
        ):
            pos["status"] = "CLOSED"
            pos["close_reason"] = (
                pos.get("capability_rejection_reason")
                or "OPTIONS_CAPABILITY_SAFETY_CLOSE"
            )
            pos["closed_at"] = now().isoformat()
            newly_closed.append(pos)
            continue

        if days >= MAX_DAYS:
            pos["status"] = "CLOSED"
            pos["close_reason"] = "MAX_HOLD_DAYS"
            pos["closed_at"] = now().isoformat()
            newly_closed.append(pos)
            continue

        pos["status"] = "OPEN"
        open_positions.append(pos)

    closed_all = _append_closed_unique_v3(
        previously_closed,
        newly_closed,
    )

    save(
        "options_v3_positions.json",
        open_positions,
    )
    save(
        "options_v3_positions_closed.json",
        closed_all,
    )

    return open_positions, closed_all

if __name__ == "__main__":
    print("===== OPTIONS V3 POSITION MANAGER =====")
    open_pos, closed_pos = update_positions()
    print(f"open_positions={len(open_pos)}")
    print(f"closed_positions={len(closed_pos)}")
