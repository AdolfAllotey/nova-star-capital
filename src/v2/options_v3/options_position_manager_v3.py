from options_data_adapter_v3 import (
    OptionsDataAdapterError,
    adapt_assignment_input_v3,
    adapt_expiration_input_v3,
)
from options_expiration_policy_v3 import evaluate_pre_expiry_close_v3
from options_assignment_guard_v3 import evaluate_assignment_risk_v3

#!/usr/bin/env python3
import json
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

def update_positions():
    portfolio = load("options_v3_portfolio_selected.json", [])
    existing = load("options_v3_positions.json", [])
    previously_closed = load("options_v3_positions_closed.json", [])

    open_positions = []
    newly_closed = []

    existing_map = {
        (p.get("ticker"), p.get("strategy")): p
        for p in existing
        if isinstance(p, dict)
    }

    for selected in portfolio:
        key = (selected.get("ticker"), selected.get("strategy"))

        if key in existing_map:
            pos = existing_map[key]
        else:
            pos = {
                "ticker": selected.get("ticker"),
                "strategy": selected.get("strategy"),
                "role": selected.get("role"),
                "opened_at": now().isoformat(),
                "entry_risk_eur": selected.get("allocated_risk_eur", selected.get("estimated_risk_eur", 0)),
                "pnl_eur": 0.0,
                "status": "OPEN",
                "source": "options_v3_portfolio_selected",
            }

        # RC2 valuation contract:
        # no synthetic PnL is permitted. Until a certified option market
        # valuation source is available, PnL must explicitly fail closed.
        pos["pnl_eur"] = None
        pos["pnl_pct"] = None
        pos["pnl_status"] = PNL_STATUS_UNAVAILABLE
        pos["pnl_provenance_status"] = PNL_PROVENANCE_STATUS

        lifecycle_input = dict(selected)
        lifecycle_input.update(pos)
        pos = evaluate_position_capabilities_v3(lifecycle_input)

        # Capability enrichment must never reintroduce synthetic valuation.
        pos["pnl_eur"] = None
        pos["pnl_pct"] = None
        pos["pnl_status"] = PNL_STATUS_UNAVAILABLE
        pos["pnl_provenance_status"] = PNL_PROVENANCE_STATUS

        opened_at = datetime.fromisoformat(pos["opened_at"])
        days = (now() - opened_at).days
        pos["days_in_trade"] = days

        if pos.get("capability_lifecycle_action") == "SIMULATED_CLOSE_REVIEW":
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
        else:
            pos["status"] = "OPEN"
            open_positions.append(pos)

    closed_all = previously_closed + newly_closed

    save("options_v3_positions.json", open_positions)
    save("options_v3_positions_closed.json", closed_all)

    return open_positions, closed_all

if __name__ == "__main__":
    print("===== OPTIONS V3 POSITION MANAGER =====")
    open_pos, closed_pos = update_positions()
    print(f"open_positions={len(open_pos)}")
    print(f"closed_positions={len(closed_pos)}")
