from datetime import datetime, timezone
from typing import List, Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _estimate_trade_risk_eur(candidate: Dict[str, Any]) -> float:
    structure = candidate.get("structure", {})
    strategy = candidate.get("strategy")

    if strategy == "covered_call":
        premium = float(structure.get("estimated_premium_per_share", 0.0))
        contracts = int(structure.get("contract_count", 0))
        return round(max(contracts * premium * 100 * 0.25, 0.0), 2)

    if strategy == "cash_secured_put":
        strike = float(structure.get("strike", 0.0))
        contracts = int(structure.get("contract_count", 1))
        premium = float(structure.get("estimated_premium_per_share", 0.0))
        gross = strike * 100 * contracts
        net_risk = gross - (premium * 100 * contracts)
        return round(max(net_risk, 0.0), 2)

    if strategy == "vertical_spread":
        return round(float(structure.get("max_loss", 0.0)), 2)

    return 0.0


def validate_options_candidates(
    candidates: List[Dict[str, Any]],
    capital_config: Dict[str, Any],
    governance: Dict[str, Any],
    existing_positions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    total_capital = float(capital_config.get("total_capital_eur", 0.0))
    max_trade_pct = float(capital_config.get("max_capital_per_trade_pct", 0.02))
    max_total_options_pct = float(capital_config.get("max_total_options_exposure_pct", 0.15))
    max_open_positions = int(capital_config.get("max_open_positions", 5))

    current_open_count = len([
        p for p in existing_positions
        if p.get("status") == "OPEN"
    ])

    current_exposure = sum(
        float(p.get("estimated_risk_eur", 0.0))
        for p in existing_positions
        if p.get("status") == "OPEN"
    )

    max_trade_risk = total_capital * max_trade_pct
    max_total_exposure = total_capital * max_total_options_pct

    validated = []

    for candidate in candidates:
        if not candidate.get("approved_signal", False):
            candidate["risk_validation"] = {
                "approved": False,
                "reason": candidate.get("blocked_reason", "signal_not_approved"),
                "estimated_risk_eur": 0.0,
                "max_trade_risk_eur": round(max_trade_risk, 2),
                "max_total_exposure_eur": round(max_total_exposure, 2),
            }
            validated.append(candidate)
            continue

        structure = candidate.get("structure", {})
        expiry_days = int(structure.get("expiry_days", 999))
        event_risk = bool(structure.get("vol_context", {}).get("event_risk", False))
        trade_risk = _estimate_trade_risk_eur(candidate)

        approved = True
        reason = "within_limits"

        if current_open_count >= max_open_positions:
            approved = False
            reason = "max_open_positions_reached"
        elif event_risk and governance.get("block_near_events", True):
            approved = False
            reason = "event_risk"
        elif expiry_days <= 7:
            approved = False
            reason = "expiry_too_short"
        elif trade_risk > max_trade_risk:
            approved = False
            reason = "trade_risk_above_limit"
        elif (current_exposure + trade_risk) > max_total_exposure:
            approved = False
            reason = "total_options_exposure_above_limit"

        candidate["risk_validation"] = {
            "approved": approved,
            "reason": reason,
            "estimated_risk_eur": round(trade_risk, 2),
            "max_trade_risk_eur": round(max_trade_risk, 2),
            "max_total_exposure_eur": round(max_total_exposure, 2),
        }

        if approved:
            current_open_count += 1
            current_exposure += trade_risk

        validated.append(candidate)

    return validated
