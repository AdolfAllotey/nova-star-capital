from statistics import mean

from src.v2.portfolio.adapters.adapter_utils import load_json, save_json


INPUT_PATH = "/opt/nsc/data/preprod/equities_offensive/reporting/dashboard_payload.json"
OUTPUT_PATH = "/opt/nsc/data/preprod/portfolio/inputs/equities_offensive_portfolio_input.json"


def clamp(value, low, high):
    return max(low, min(high, value))


def _derive_target_weight(market_regime: str, confidence: float) -> float:
    regime = (market_regime or "").lower()
    if regime == "risk_on":
        return 0.25 if confidence >= 0.75 else 0.20
    if regime == "neutral":
        return 0.12
    if regime == "risk_off":
        return 0.00
    return 0.10


def compute_dynamic_offensive_confidence(market, kpis, top_voted, risk_decisions, execution_plan):
    market_conf = float(market.get("confidence", kpis.get("market_confidence", 0.0)) or 0.0)

    meta_scores = []
    if isinstance(top_voted, list):
        for item in top_voted:
            if isinstance(item, dict):
                try:
                    meta_scores.append(float(item.get("meta_score", 0.0) or 0.0))
                except Exception:
                    pass

    avg_meta = mean(meta_scores) if meta_scores else 0.0
    meta_component = clamp(avg_meta / 100.0, 0.0, 1.0)

    allowed_ratio = 0.0
    if isinstance(risk_decisions, list) and risk_decisions:
        allowed = len([x for x in risk_decisions if isinstance(x, dict) and x.get("allowed")])
        allowed_ratio = allowed / len(risk_decisions)
    elif int(kpis.get("risk_decisions_count", 0) or 0) > 0:
        allowed_ratio = 0.5

    orders = execution_plan.get("orders", []) if isinstance(execution_plan, dict) else []
    orders_count = len(orders) if isinstance(orders, list) else 0
    order_component = 0.04 if orders_count > 0 else -0.03

    action_policy = (
        kpis.get("action_policy")
        or execution_plan.get("action_policy")
        or "unknown"
    )
    policy_penalty = 0.05 if action_policy in {"BLOCKED", "NO_TRADE", "SIMULATED_ONLY"} else 0.0

    confidence = (
        market_conf * 0.45
        + meta_component * 0.35
        + allowed_ratio * 0.20
        + order_component
        - policy_penalty
    )

    confidence = clamp(confidence, 0.35, 0.95)

    return round(confidence, 4), {
        "method": "market_plus_votes_plus_risk",
        "market_confidence": round(market_conf, 4),
        "avg_meta_score": round(avg_meta, 4),
        "meta_component": round(meta_component, 4),
        "risk_allowed_ratio": round(allowed_ratio, 4),
        "orders_count": orders_count,
        "order_component": round(order_component, 4),
        "action_policy": action_policy,
        "policy_penalty": round(policy_penalty, 4),
    }


def export_offensive_equities_to_portfolio_input(
    input_path: str = INPUT_PATH,
    output_path: str = OUTPUT_PATH
):
    data = load_json(input_path)

    kpis = data.get("kpis", {})
    market = data.get("market_regime", {})
    top_voted = data.get("top_voted", [])
    risk_decisions = data.get("risk_decisions", [])
    execution_plan = data.get("execution_plan", {})

    regime = market.get("regime", kpis.get("market_regime", "unknown"))
    confidence, confidence_details = compute_dynamic_offensive_confidence(
        market,
        kpis,
        top_voted,
        risk_decisions,
        execution_plan,
    )
    target_weight = _derive_target_weight(regime, confidence)

    allocation = {}
    if top_voted:
        weight_per_symbol = round(1.0 / len(top_voted), 4)
        allocation = {
            item.get("symbol", f"asset_{i}"): weight_per_symbol
            for i, item in enumerate(top_voted, start=1)
        }

    payload = {
        "brick": "equities_offensive",
        "enabled": True,
        "portfolio_role": "alpha_directional",
        "signal_type": "allocation_proposal",
        "target_weight": target_weight,
        "confidence": confidence,
        "regime": regime,
        "allocation": allocation,
        "drivers": {
            "market_regime": regime,
            "signals_count": kpis.get("signals_count", 0),
            "voted_count": kpis.get("voted_count", 0),
            "risk_decisions_count": kpis.get("risk_decisions_count", 0),
            "execution_candidate_orders": kpis.get("execution_candidate_orders", 0),
            "action_policy": kpis.get("action_policy", execution_plan.get("action_policy", "unknown")),
            "confidence_details": confidence_details,
        },
        "risk_flags": {
            "execution_blocked": execution_plan.get("action_policy") == "SIMULATED_ONLY",
            "open_positions": kpis.get("open_positions", 0),
            "risk_decisions_allowed": len([x for x in risk_decisions if x.get("allowed")]) if isinstance(risk_decisions, list) else 0
        },
        "inertia_profile": {
            "rebalance_frequency": "medium",
            "max_weight_change_per_cycle": 0.04,
            "min_threshold_to_rebalance": 0.03
        },
        "execution_mode": "signal_only",
        "funding_pool": "ibkr_pool",
        "source_file": input_path
    }

    save_json(payload, output_path)
    return payload


if __name__ == "__main__":
    result = export_offensive_equities_to_portfolio_input()
    print(result)
