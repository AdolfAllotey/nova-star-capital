from __future__ import annotations

from dataclasses import asdict, dataclass
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
