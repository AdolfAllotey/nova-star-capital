#!/usr/bin/env python3
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
    max_total_options_exposure_pct: float = 0.50,
    max_trade_risk_pct: float = 0.20,
) -> Dict[str, Any]:
    max_total_risk = capital_eur * max_total_options_exposure_pct
    max_trade_risk = capital_eur * max_trade_risk_pct

    selected = []
    rejected = []
    used_risk = 0.0

    deduped = deduplicate_by_ticker(candidates)

    for c in deduped:
        risk = float(c.get("estimated_risk_eur") or 0)

        if risk <= 0:
            rejected.append({**c, "portfolio_reject_reason": "missing_risk"})
            continue

        if risk > max_trade_risk:
            rejected.append({**c, "portfolio_reject_reason": "trade_risk_above_cap"})
            continue

        if used_risk + risk > max_total_risk:
            rejected.append({**c, "portfolio_reject_reason": "total_options_risk_cap"})
            continue

        allocation_weight = risk / capital_eur

        selected.append({
            **c,
            "allocated_risk_eur": round(risk, 2),
            "target_weight": round(allocation_weight, 4),
            "portfolio_status": "SELECTED",
        })

        used_risk += risk

    return {
        "capital_eur": capital_eur,
        "max_total_options_exposure_pct": max_total_options_exposure_pct,
        "max_trade_risk_pct": max_trade_risk_pct,
        "max_total_risk_eur": round(max_total_risk, 2),
        "max_trade_risk_eur": round(max_trade_risk, 2),
        "used_risk_eur": round(used_risk, 2),
        "used_risk_pct": round(used_risk / capital_eur, 4) if capital_eur else 0,
        "selected_count": len(selected),
        "rejected_count": len(rejected),
        "selected": selected,
        "rejected": rejected,
    }
