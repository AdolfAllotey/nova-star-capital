#!/usr/bin/env python3
from math import isfinite
from typing import List, Dict, Any

ROLE_PRIORITY = {
    "alpha": 4,
    "hedge": 4,
    "yield": 3,
    "entry_yield": 2,
    "neutral": 1,
}

STRATEGY_PRIORITY = {
    "bull_call_spread": 5,
    "bear_put_spread": 5,
    "covered_call": 4,
    "cash_secured_put": 3,
    "bull_put_spread": 3,
    "long_call": 2,
    "neutral_spread": 1,
}

def rank_candidate(c: Dict[str, Any]) -> float:
    role = c.get("role", "neutral")
    strategy = c.get("strategy", "neutral_spread")
    score = float(c.get("score") or 0)
    risk = float(c.get("estimated_risk_eur") or 0)

    role_bonus = ROLE_PRIORITY.get(role, 0) * 10
    strategy_bonus = STRATEGY_PRIORITY.get(strategy, 0) * 5
    risk_penalty = min(risk / 1000, 10)

    return round(score + role_bonus + strategy_bonus - risk_penalty, 2)

def deduplicate_by_ticker(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best = {}

    for c in candidates:
        ticker = c.get("ticker")
        if not ticker:
            continue

        c = dict(c)
        c["portfolio_rank_score"] = rank_candidate(c)

        if ticker not in best:
            best[ticker] = c
            continue

        if c["portfolio_rank_score"] > best[ticker]["portfolio_rank_score"]:
            best[ticker] = c

    return sorted(best.values(), key=lambda x: x.get("portfolio_rank_score", 0), reverse=True)

def allocate_portfolio(
    candidates: List[Dict[str, Any]],
    capital_eur: float = 10000.0,
    max_total_options_exposure_pct: float = 0.5,
    max_trade_risk_pct: float = 0.2,
    existing_used_risk_eur: float = 0.0,
    existing_open_positions_count: int = 0,
    max_open_positions: int = 5,
) -> Dict[str, Any]:
    max_total_risk = (
        capital_eur
        * max_total_options_exposure_pct
    )
    max_trade_risk = (
        capital_eur
        * max_trade_risk_pct
    )

    try:
        existing_used_risk = float(
            existing_used_risk_eur
        )
    except (TypeError, ValueError):
        raise ValueError(
            "existing_used_risk_eur must be numeric"
        )

    if (
        not isfinite(existing_used_risk)
        or existing_used_risk < 0.0
    ):
        raise ValueError(
            "existing_used_risk_eur must be finite and non-negative"
        )

    def _strict_non_bool_integer(value, name):
        if isinstance(value, bool):
            raise ValueError(
                f"{name} must be an integer"
            )

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"{name} must be an integer"
            )

        if (
            not isfinite(numeric)
            or not numeric.is_integer()
        ):
            raise ValueError(
                f"{name} must be an integer"
            )

        return int(numeric)

    existing_open_count = _strict_non_bool_integer(
        existing_open_positions_count,
        "existing_open_positions_count",
    )
    position_limit = _strict_non_bool_integer(
        max_open_positions,
        "max_open_positions",
    )

    if existing_open_count < 0:
        raise ValueError(
            "existing_open_positions_count must be non-negative"
        )

    if position_limit <= 0:
        raise ValueError(
            "max_open_positions must be positive"
        )

    selected = []
    rejected = []

    used_risk = existing_used_risk
    new_allocated_risk = 0.0

    deduped = deduplicate_by_ticker(candidates)

    for c in deduped:
        risk = float(
            c.get("estimated_risk_eur") or 0
        )

        if risk <= 0:
            rejected.append(
                {
                    **c,
                    "portfolio_reject_reason":
                        "missing_risk",
                }
            )
            continue

        if risk > max_trade_risk:
            rejected.append(
                {
                    **c,
                    "portfolio_reject_reason":
                        "trade_risk_above_cap",
                }
            )
            continue

        if (
            existing_open_count + len(selected)
            >= position_limit
        ):
            rejected.append(
                {
                    **c,
                    "portfolio_reject_reason":
                        "max_open_positions_reached",
                }
            )
            continue

        if used_risk + risk > max_total_risk:
            rejected.append(
                {
                    **c,
                    "portfolio_reject_reason":
                        "total_options_risk_cap",
                }
            )
            continue

        allocation_weight = risk / capital_eur

        selected.append(
            {
                **c,
                "allocated_risk_eur":
                    round(risk, 2),
                "target_weight":
                    round(allocation_weight, 4),
                "portfolio_status":
                    "SELECTED",
            }
        )

        used_risk += risk
        new_allocated_risk += risk

    available_before_new = max(
        0.0,
        max_total_risk - existing_used_risk,
    )

    available_after_new = max(
        0.0,
        max_total_risk - used_risk,
    )

    return {
        "capital_eur": capital_eur,
        "max_total_options_exposure_pct":
            max_total_options_exposure_pct,
        "max_trade_risk_pct":
            max_trade_risk_pct,
        "max_total_risk_eur":
            round(max_total_risk, 2),
        "max_trade_risk_eur":
            round(max_trade_risk, 2),
        "existing_used_risk_eur":
            round(existing_used_risk, 2),
        "available_risk_eur_before_new":
            round(available_before_new, 2),
        "new_allocated_risk_eur":
            round(new_allocated_risk, 2),
        "used_risk_eur":
            round(used_risk, 2),
        "available_risk_eur_after_new":
            round(available_after_new, 2),
        "used_risk_pct":
            round(
                used_risk / capital_eur,
                4,
            )
            if capital_eur
            else 0,
        "risk_cap_breached_at_start":
            existing_used_risk > max_total_risk,
        "existing_open_positions_count":
            existing_open_count,
        "max_open_positions":
            position_limit,
        "planned_open_positions_count":
            existing_open_count + len(selected),
        "position_cap_reached":
            (
                existing_open_count + len(selected)
                >= position_limit
            ),
        "position_cap_breached_at_start":
            existing_open_count > position_limit,
        "selected_count": len(selected),
        "rejected_count": len(rejected),
        "selected": selected,
        "rejected": rejected,
    }
