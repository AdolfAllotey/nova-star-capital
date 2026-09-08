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
from math import isfinite

BASE = Path("/opt/nsc/data/preprod/options_v3")

MAX_DAYS = 45

TAKE_PROFIT_PCT = 20.0
STOP_LOSS_PCT = -20.0
CERTIFIED_PNL_PCT_STATUS = (
    "AVAILABLE_CERTIFIED_ENTRY_RISK"
)

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

        certified_pnl_pct = None

        if (
            enriched.get("pnl_pct_status")
            == CERTIFIED_PNL_PCT_STATUS
        ):
            try:
                candidate_pnl_pct = float(
                    enriched.get("pnl_pct")
                )
            except (TypeError, ValueError):
                candidate_pnl_pct = None

            if (
                candidate_pnl_pct is not None
                and isfinite(candidate_pnl_pct)
            ):
                certified_pnl_pct = candidate_pnl_pct

        expiry_decision = evaluate_pre_expiry_close_v3(
            expiration=expiration_input.expiration,
            current_timestamp=(
                expiration_input.valuation_timestamp
            ),
            position_status=str(
                enriched.get("status") or "OPEN"
            ),
            pnl_pct=certified_pnl_pct,
            profit_take_pct=TAKE_PROFIT_PCT,
            stop_loss_pct=STOP_LOSS_PCT,
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

        expiry_close = bool(
            expiry_payload.get(
                "pre_expiry_close_required"
            )
            or expiry_payload.get("force_close")
            or expiry_payload.get("should_close")
        )

        assignment_close = bool(
            assignment_payload.get("mandatory_close")
            or assignment_payload.get("force_close")
            or assignment_payload.get("should_close")
        )

        force_close = bool(
            expiry_close or assignment_close
        )

        capability_close_reason = None
        capability_close_category = None

        if expiry_close:
            capability_close_reason = (
                expiry_payload.get("close_reason")
                or "OPTIONS_EXPIRATION_POLICY_CLOSE"
            )

            if capability_close_reason in {
                "profit_take_threshold_reached",
                "stop_loss_threshold_reached",
            }:
                capability_close_category = (
                    "PERFORMANCE_EXIT"
                )
            else:
                capability_close_category = (
                    "EXPIRATION_EXIT"
                )

        elif assignment_close:
            capability_close_reason = (
                assignment_payload.get("guard_reason")
                or "OPTIONS_ASSIGNMENT_GUARD_CLOSE"
            )
            capability_close_category = (
                "ASSIGNMENT_RISK_EXIT"
            )

        enriched["capability_lifecycle_action"] = (
            "SIMULATED_CLOSE_REVIEW"
            if force_close
            else "HOLD"
        )
        enriched["capability_close_reason"] = (
            capability_close_reason
        )
        enriched["capability_close_category"] = (
            capability_close_category
        )

        return enriched

    except OptionsDataAdapterError as exc:
        enriched["capability_lifecycle_action"] = (
            "SIMULATED_CLOSE_REVIEW"
        )
        enriched["capability_rejection_reason"] = str(exc)
        enriched["capability_close_reason"] = str(exc)
        enriched["capability_close_category"] = "SAFETY_EXIT"
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


def _certified_entry_risk_provenance_v3(
    selected: dict,
) -> dict | None:
    if selected.get("sizing_currency") != "EUR":
        return None

    if (
        selected.get("contract_economics_source_currency")
        != "USD"
    ):
        return None

    fx = selected.get("sizing_fx")
    if not isinstance(fx, dict) or not fx:
        return None

    if (
        fx.get("base_currency") != "USD"
        or fx.get("quote_currency") != "EUR"
    ):
        return None

    try:
        fx_rate = float(fx.get("rate"))
        estimated = float(selected.get("estimated_risk_eur"))
        allocated = float(selected.get("allocated_risk_eur"))
    except (TypeError, ValueError):
        return None

    if (
        not isfinite(fx_rate)
        or fx_rate <= 0.0
        or not isfinite(estimated)
        or estimated <= 0.0
        or not isfinite(allocated)
        or allocated <= 0.0
    ):
        return None

    if abs(allocated - round(estimated, 2)) > 1e-9:
        return None

    provider = str(fx.get("provider") or "").strip()
    market_timestamp = str(
        fx.get("market_timestamp") or ""
    ).strip()
    retrieved_at = str(
        fx.get("retrieved_at") or ""
    ).strip()

    if not provider or not market_timestamp or not retrieved_at:
        return None

    return {
        "contract_version": 1,
        "currency": "EUR",
        "source": "allocated_risk_eur",
        "estimated_risk_eur": estimated,
        "allocated_risk_eur": allocated,
        "sizing_currency": "EUR",
        "contract_economics_source_currency": "USD",
        "sizing_fx": dict(fx),
    }


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

    entry_risk_provenance = (
        _certified_entry_risk_provenance_v3(selected)
    )

    if entry_risk_provenance is not None:
        pos["entry_risk_currency"] = "EUR"
        pos["entry_risk_source"] = "allocated_risk_eur"
        pos["entry_risk_contract_version"] = 1
        pos["entry_risk_provenance"] = entry_risk_provenance

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


def calculate_open_risk_v3(
    positions: list,
) -> float:
    if not isinstance(positions, list):
        raise RuntimeError(
            "options_v3_open_risk: positions must be a list"
        )

    total = 0.0

    for position in positions:
        if not isinstance(position, dict):
            continue

        if str(
            position.get("status") or "OPEN"
        ).upper() != "OPEN":
            continue

        raw_risk = position.get("entry_risk_eur")

        try:
            risk = float(raw_risk)
        except (TypeError, ValueError):
            raise RuntimeError(
                "options_v3_open_risk: "
                "entry_risk_eur must be numeric"
            )

        if not isfinite(risk) or risk < 0.0:
            raise RuntimeError(
                "options_v3_open_risk: "
                "entry_risk_eur must be finite and non-negative"
            )

        total += risk

    return round(total, 6)


def _apply_certified_valuation_v3(
    position: dict,
    valuation: dict | None,
) -> dict:
    enriched = dict(position)

    if valuation is None:
        enriched["pnl_eur"] = None
        enriched["pnl_pct"] = None
        enriched["pnl_status"] = PNL_STATUS_UNAVAILABLE
        enriched["pnl_provenance_status"] = (
            PNL_PROVENANCE_STATUS
        )
        return enriched

    if not isinstance(valuation, dict):
        raise RuntimeError(
            "options_v3_valuation: dict required"
        )

    if (
        valuation.get("position_id")
        != position.get("position_id")
        or valuation.get("structure_id")
        != position.get("structure_id")
    ):
        raise RuntimeError(
            "options_v3_valuation: position identity mismatch"
        )

    if (
        valuation.get("read_only_valuation") is not True
        or valuation.get("real_execution_allowed") is not False
        or valuation.get("valuation_currency") != "EUR"
        or valuation.get("contract_economics_currency") != "USD"
        or valuation.get("valuation_method")
        != "EXECUTABLE_BID_ASK_LIQUIDATION"
    ):
        raise RuntimeError(
            "options_v3_valuation: uncertified valuation contract"
        )

    fx_provenance = valuation.get("fx_provenance")
    if not isinstance(fx_provenance, dict) or not fx_provenance:
        raise RuntimeError(
            "options_v3_valuation: FX provenance required"
        )

    if (
        fx_provenance.get("base_currency") != "USD"
        or fx_provenance.get("quote_currency") != "EUR"
    ):
        raise RuntimeError(
            "options_v3_valuation: USD/EUR FX provenance required"
        )

    try:
        valuation_fx_rate = float(
            valuation.get("usd_eur_rate")
        )
        provenance_fx_rate = float(
            fx_provenance.get("rate")
        )
    except (TypeError, ValueError):
        raise RuntimeError(
            "options_v3_valuation: valid FX rate required"
        )

    if (
        not isfinite(valuation_fx_rate)
        or valuation_fx_rate <= 0.0
        or not isfinite(provenance_fx_rate)
        or provenance_fx_rate <= 0.0
        or abs(
            valuation_fx_rate - provenance_fx_rate
        ) > 1e-12
    ):
        raise RuntimeError(
            "options_v3_valuation: FX rate provenance mismatch"
        )

    for field in (
        "provider",
        "market_timestamp",
        "retrieved_at",
    ):
        if not str(
            fx_provenance.get(field) or ""
        ).strip():
            raise RuntimeError(
                "options_v3_valuation: incomplete FX provenance"
            )

    try:
        pnl_eur = float(valuation.get("pnl_eur"))
    except (TypeError, ValueError):
        raise RuntimeError(
            "options_v3_valuation: pnl_eur must be numeric"
        )

    if not isfinite(pnl_eur):
        raise RuntimeError(
            "options_v3_valuation: pnl_eur must be finite"
        )

    enriched.update(valuation)
    enriched["pnl_eur"] = pnl_eur
    enriched["pnl_status"] = "AVAILABLE_CERTIFIED_MARKET_VALUATION"
    enriched["pnl_provenance_status"] = (
        "CERTIFIED_OPTION_MARK_PROVENANCE"
    )

    entry_contract = position.get(
        "entry_risk_contract_version"
    )
    entry_currency = position.get(
        "entry_risk_currency"
    )
    entry_source = position.get(
        "entry_risk_source"
    )
    entry_provenance = position.get(
        "entry_risk_provenance"
    )

    entry_certified = (
        entry_contract == 1
        and entry_currency == "EUR"
        and entry_source == "allocated_risk_eur"
        and isinstance(entry_provenance, dict)
        and entry_provenance.get("contract_version") == 1
        and entry_provenance.get("currency") == "EUR"
        and entry_provenance.get("source")
        == "allocated_risk_eur"
    )

    if not entry_certified:
        enriched["pnl_pct"] = None
        enriched["pnl_pct_status"] = (
            "ENTRY_RISK_EUR_PROVENANCE_REQUIRED"
        )
        return enriched

    try:
        entry_risk_eur = float(
            position.get("entry_risk_eur")
        )
        provenance_entry_risk = float(
            entry_provenance.get("allocated_risk_eur")
        )
    except (TypeError, ValueError):
        enriched["pnl_pct"] = None
        enriched["pnl_pct_status"] = (
            "ENTRY_RISK_EUR_PROVENANCE_INVALID"
        )
        return enriched

    if (
        not isfinite(entry_risk_eur)
        or entry_risk_eur <= 0.0
        or not isfinite(provenance_entry_risk)
        or provenance_entry_risk <= 0.0
        or abs(entry_risk_eur - provenance_entry_risk) > 1e-9
    ):
        enriched["pnl_pct"] = None
        enriched["pnl_pct_status"] = (
            "ENTRY_RISK_EUR_PROVENANCE_INVALID"
        )
        return enriched

    enriched["pnl_pct"] = round(
        (pnl_eur / entry_risk_eur) * 100.0,
        8,
    )
    enriched["pnl_pct_status"] = (
        "AVAILABLE_CERTIFIED_ENTRY_RISK"
    )

    return enriched


def _evaluate_position_lifecycle_v3(
    stored_position: dict,
    selected_context: dict | None = None,
    valuation: dict | None = None,
) -> tuple[dict | None, dict | None]:
    pos = dict(stored_position)

    lifecycle_input = dict(pos)

    if selected_context is not None:
        lifecycle_input.update(selected_context)

        # Immutable opening identity/state always belongs
        # to the canonical inventory.
        lifecycle_input["position_id"] = pos["position_id"]
        lifecycle_input["structure_id"] = pos["structure_id"]
        lifecycle_input["opened_at"] = pos["opened_at"]
        lifecycle_input["entry_risk_eur"] = pos.get(
            "entry_risk_eur",
            0,
        )

        for field in (
            "entry_risk_currency",
            "entry_risk_source",
            "entry_risk_contract_version",
            "entry_risk_provenance",
        ):
            if field in pos:
                lifecycle_input[field] = pos[field]
            else:
                lifecycle_input.pop(field, None)

    lifecycle_input = _apply_certified_valuation_v3(
        lifecycle_input,
        valuation,
    )

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

    # Certified valuation state survives capability enrichment.
    # Identity/opening state above remains canonical.

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
            pos.get("capability_close_reason")
            or pos.get("capability_rejection_reason")
            or "OPTIONS_CAPABILITY_SAFETY_CLOSE"
        )
        pos["close_category"] = (
            pos.get("capability_close_category")
            or "SAFETY_EXIT"
        )
        pos["closed_at"] = now().isoformat()
        return None, pos

    if days >= MAX_DAYS:
        pos["status"] = "CLOSED"
        pos["close_reason"] = "MAX_HOLD_DAYS"
        pos["close_category"] = "TIME_EXIT"
        pos["closed_at"] = now().isoformat()
        return None, pos

    pos["status"] = "OPEN"

    return pos, None


def reconcile_existing_positions_v3(
    valuations_by_position_id: dict | None = None,
):
    if valuations_by_position_id is None:
        valuations_by_position_id = {}

    if not isinstance(valuations_by_position_id, dict):
        raise RuntimeError(
            "options_v3_valuation_map: dict required"
        )

    existing_raw = load(
        "options_v3_positions.json",
        [],
    )
    previously_closed = load(
        "options_v3_positions_closed.json",
        [],
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

    open_positions = []
    newly_closed = []

    for stored_position in existing:
        opened, closed = (
            _evaluate_position_lifecycle_v3(
                stored_position,
                valuation=valuations_by_position_id.get(
                    stored_position["position_id"]
                ),
            )
        )

        if opened is not None:
            open_positions.append(opened)

        if closed is not None:
            newly_closed.append(closed)

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


def open_selected_positions_v3(
    portfolio: list,
):
    if not isinstance(portfolio, list):
        raise RuntimeError(
            "options_v3_portfolio_selected must be a list"
        )

    existing_raw = load(
        "options_v3_positions.json",
        [],
    )
    previously_closed = load(
        "options_v3_positions_closed.json",
        [],
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

        structure_id = build_structure_id_v3(
            selected
        )

        if structure_id in selected_map:
            # Same exact contract structure in one
            # allocation run: one canonical opening only.
            continue

        selected_map[structure_id] = selected

    open_positions = list(existing)
    newly_closed = []

    for structure_id, selected in selected_map.items():
        if structure_id in existing_map:
            # Persistent existing position has already
            # completed lifecycle evaluation this cycle.
            continue

        new_position = _build_new_position_v3(
            selected
        )

        opened, closed = (
            _evaluate_position_lifecycle_v3(
                new_position,
                selected_context=selected,
            )
        )

        if opened is not None:
            open_positions.append(opened)
            existing_map[structure_id] = opened

        if closed is not None:
            newly_closed.append(closed)

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


def update_positions(
    portfolio_override=None,
):
    # Backward-compatible one-shot wrapper.
    #
    # Existing inventory is reconciled exactly once.
    # New selected structures are then opened without
    # reevaluating surviving existing positions.
    reconcile_existing_positions_v3()

    if portfolio_override is None:
        portfolio = load(
            "options_v3_portfolio_selected.json",
            [],
        )
    else:
        portfolio = portfolio_override

    return open_selected_positions_v3(
        portfolio
    )

if __name__ == "__main__":
    print("===== OPTIONS V3 POSITION MANAGER =====")
    open_pos, closed_pos = update_positions()
    print(f"open_positions={len(open_pos)}")
    print(f"closed_positions={len(closed_pos)}")
