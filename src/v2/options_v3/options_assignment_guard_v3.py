from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class AssignmentGuardResultV3:
    assignment_risk: str
    assignment_possible: bool
    exercise_possible: bool
    mandatory_close: bool
    guard_reason: str
    guard_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_structure_assignment_risk_v3(
    *,
    contract_legs,
    underlying_price,
    days_to_expiry,
    position_status,
    exercise_style="american",
    assignment_close_threshold_days=3,
):
    """
    Evaluate assignment/exercise semantics for an entire option structure.

    Any SELL leg may be assigned. Any BUY leg may be exercised.
    The aggregate risk is the highest risk across short legs.
    """
    if not isinstance(contract_legs, list) or not contract_legs:
        return {
            "assignment_risk": "unknown",
            "assignment_possible": False,
            "exercise_possible": False,
            "mandatory_close": True,
            "guard_reason": "missing_contract_legs",
            "guard_valid": False,
            "short_leg_count": 0,
            "long_leg_count": 0,
            "leg_assessments": [],
        }

    try:
        spot = float(underlying_price)
    except (TypeError, ValueError):
        spot = float("nan")

    if not isfinite(spot) or spot <= 0:
        return {
            "assignment_risk": "unknown",
            "assignment_possible": False,
            "exercise_possible": False,
            "mandatory_close": True,
            "guard_reason": "invalid_underlying_price",
            "guard_valid": False,
            "short_leg_count": 0,
            "long_leg_count": 0,
            "leg_assessments": [],
        }

    risk_order = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
        "unknown": 5,
    }

    short_results = []
    long_leg_count = 0

    for leg_index, leg in enumerate(contract_legs):
        if not isinstance(leg, dict):
            return {
                "assignment_risk": "unknown",
                "assignment_possible": False,
                "exercise_possible": False,
                "mandatory_close": True,
                "guard_reason": "invalid_contract_leg",
                "guard_valid": False,
                "short_leg_count": len(short_results),
                "long_leg_count": long_leg_count,
                "invalid_leg_index": leg_index,
                "leg_assessments": short_results,
            }

        side = str(leg.get("side") or "").strip().upper()
        option_type = str(
            leg.get("option_type") or ""
        ).strip().lower()

        try:
            strike = float(leg.get("strike"))
        except (TypeError, ValueError):
            strike = float("nan")

        if not isfinite(strike) or strike <= 0:
            return {
                "assignment_risk": "unknown",
                "assignment_possible": False,
                "exercise_possible": False,
                "mandatory_close": True,
                "guard_reason": "invalid_contract_leg_strike",
                "guard_valid": False,
                "short_leg_count": len(short_results),
                "long_leg_count": long_leg_count,
                "invalid_leg_index": leg_index,
                "leg_assessments": short_results,
            }

        if option_type in {"c", "call"}:
            normalized_type = "call"
            moneyness = spot - strike
        elif option_type in {"p", "put"}:
            normalized_type = "put"
            moneyness = strike - spot
        else:
            return {
                "assignment_risk": "unknown",
                "assignment_possible": False,
                "exercise_possible": False,
                "mandatory_close": True,
                "guard_reason": "unsupported_contract_leg_option_type",
                "guard_valid": False,
                "short_leg_count": len(short_results),
                "long_leg_count": long_leg_count,
                "invalid_leg_index": leg_index,
                "leg_assessments": short_results,
            }

        if side == "BUY":
            long_leg_count += 1
            continue

        if side != "SELL":
            return {
                "assignment_risk": "unknown",
                "assignment_possible": False,
                "exercise_possible": False,
                "mandatory_close": True,
                "guard_reason": "unsupported_contract_leg_side",
                "guard_valid": False,
                "short_leg_count": len(short_results),
                "long_leg_count": long_leg_count,
                "invalid_leg_index": leg_index,
                "leg_assessments": short_results,
            }

        result = evaluate_assignment_risk_v3(
            option_type=normalized_type,
            strategy=(
                "short_call"
                if normalized_type == "call"
                else "short_put"
            ),
            days_to_expiry=days_to_expiry,
            moneyness=moneyness,
            position_status=position_status,
            exercise_style=exercise_style,
            assignment_close_threshold_days=(
                assignment_close_threshold_days
            ),
        )

        result = dict(result)
        result["contract_symbol"] = leg.get(
            "contract_symbol"
        )
        result["side"] = side
        result["strike"] = strike
        result["moneyness"] = moneyness

        short_results.append(result)

    if not short_results:
        return {
            "assignment_risk": "none",
            "assignment_possible": False,
            "exercise_possible": long_leg_count > 0,
            "mandatory_close": False,
            "guard_reason": (
                "long_structure_exercise_possible"
                if long_leg_count > 0
                else "no_assignable_short_option_leg"
            ),
            "guard_valid": True,
            "short_leg_count": 0,
            "long_leg_count": long_leg_count,
            "leg_assessments": [],
        }

    highest = max(
        short_results,
        key=lambda row: risk_order.get(
            str(row.get("assignment_risk")),
            5,
        ),
    )

    mandatory_close = any(
        bool(row.get("mandatory_close"))
        for row in short_results
    )

    return {
        "assignment_risk": highest.get(
            "assignment_risk",
            "unknown",
        ),
        "assignment_possible": True,
        "exercise_possible": long_leg_count > 0,
        "mandatory_close": mandatory_close,
        "guard_reason": (
            highest.get("guard_reason")
            or "short_leg_assignment_possible"
        ),
        "guard_valid": all(
            row.get("guard_valid") is True
            for row in short_results
        ),
        "short_leg_count": len(short_results),
        "long_leg_count": long_leg_count,
        "leg_assessments": short_results,
    }



def evaluate_assignment_risk_v3(
    *,
    option_type: str,
    strategy: str,
    days_to_expiry: int,
    moneyness: float,
    position_status: str,
    exercise_style: str = "american",
    assignment_close_threshold_days: int = 3,
    in_the_money_threshold: float = 0.0,
) -> dict[str, Any]:
    normalized_type = str(option_type).strip().lower()
    normalized_strategy = str(strategy).strip().lower()
    normalized_status = str(position_status).strip().lower()
    normalized_style = str(exercise_style).strip().lower()

    if normalized_type in {"c", "call"}:
        normalized_type = "call"
    elif normalized_type in {"p", "put"}:
        normalized_type = "put"
    else:
        return AssignmentGuardResultV3(
            assignment_risk="unknown",
            assignment_possible=False,
            exercise_possible=False,
            mandatory_close=True,
            guard_reason="unsupported_option_type",
            guard_valid=False,
        ).to_dict()

    try:
        dte = int(days_to_expiry)
        money = float(moneyness)
    except (TypeError, ValueError):
        return AssignmentGuardResultV3(
            assignment_risk="unknown",
            assignment_possible=False,
            exercise_possible=False,
            mandatory_close=True,
            guard_reason="invalid_assignment_inputs",
            guard_valid=False,
        ).to_dict()

    if normalized_status in {
        "closed",
        "expired",
        "assigned",
        "exercised",
    }:
        return AssignmentGuardResultV3(
            assignment_risk="none",
            assignment_possible=False,
            exercise_possible=False,
            mandatory_close=False,
            guard_reason="position_already_terminal",
            guard_valid=True,
        ).to_dict()

    short_option_strategies = {
        "cash_secured_put",
        "covered_call",
        "short_put",
        "short_call",
        "credit_spread",
        "bull_put_spread",
        "bear_call_spread",
        "iron_condor",
    }

    long_option_strategies = {
        "long_call",
        "long_put",
        "debit_spread",
        "bull_call_spread",
        "bear_put_spread",
    }

    assignment_possible = (
        normalized_strategy in short_option_strategies
    )

    exercise_possible = (
        normalized_strategy in long_option_strategies
    )

    american_style = normalized_style == "american"
    in_the_money = money > float(in_the_money_threshold)
    near_expiry = dte <= int(
        assignment_close_threshold_days
    )

    if assignment_possible and american_style:
        if in_the_money and near_expiry:
            return AssignmentGuardResultV3(
                assignment_risk="critical",
                assignment_possible=True,
                exercise_possible=False,
                mandatory_close=True,
                guard_reason=(
                    "short_american_option_itm_near_expiry"
                ),
                guard_valid=True,
            ).to_dict()

        if in_the_money:
            return AssignmentGuardResultV3(
                assignment_risk="high",
                assignment_possible=True,
                exercise_possible=False,
                mandatory_close=False,
                guard_reason="short_american_option_itm",
                guard_valid=True,
            ).to_dict()

        if near_expiry:
            return AssignmentGuardResultV3(
                assignment_risk="medium",
                assignment_possible=True,
                exercise_possible=False,
                mandatory_close=True,
                guard_reason="short_option_near_expiry",
                guard_valid=True,
            ).to_dict()

        return AssignmentGuardResultV3(
            assignment_risk="low",
            assignment_possible=True,
            exercise_possible=False,
            mandatory_close=False,
            guard_reason="short_option_assignment_possible",
            guard_valid=True,
        ).to_dict()

    if assignment_possible:
        mandatory_close = in_the_money and near_expiry

        return AssignmentGuardResultV3(
            assignment_risk=(
                "high"
                if mandatory_close
                else "low"
            ),
            assignment_possible=True,
            exercise_possible=False,
            mandatory_close=mandatory_close,
            guard_reason=(
                "european_short_option_near_expiry"
                if mandatory_close
                else "european_assignment_at_expiry_only"
            ),
            guard_valid=True,
        ).to_dict()

    if exercise_possible:
        mandatory_close = near_expiry

        return AssignmentGuardResultV3(
            assignment_risk="none",
            assignment_possible=False,
            exercise_possible=True,
            mandatory_close=mandatory_close,
            guard_reason=(
                "long_option_close_before_expiry"
                if mandatory_close
                else "long_option_exercise_possible"
            ),
            guard_valid=True,
        ).to_dict()

    return AssignmentGuardResultV3(
        assignment_risk="unknown",
        assignment_possible=False,
        exercise_possible=False,
        mandatory_close=True,
        guard_reason="strategy_assignment_semantics_unknown",
        guard_valid=False,
    ).to_dict()
