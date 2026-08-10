from statistics import mean

from src.v2.portfolio.adapters.adapter_utils import load_json, save_json


INPUT_PATH = "/opt/nsc/data/preprod/trading/capital_allocation.json"
TRADING_PLAN_PATH = "/opt/nsc/data/preprod/trading/trading_plan.json"
PORTFOLIO_OVERVIEW_PATH = "/opt/nsc/data/preprod/analysis/portfolio_overview.json"
SIGNAL_VOTES_PATH = "/opt/nsc/data/preprod/analysis/signal_votes.json"
OUTPUT_PATH = "/opt/nsc/data/preprod/portfolio/inputs/crypto_portfolio_input.json"


def clamp(value, low, high):
    return max(low, min(high, value))


def compute_dynamic_crypto_confidence(regime: str, signal_votes):
    base_by_regime = {
        "risk_on": 0.68,
        "bull": 0.72,
        "neutral": 0.55,
        "balanced": 0.55,
        "risk_off": 0.40,
        "bear": 0.35,
    }
    base = base_by_regime.get(regime, 0.50)

    if not isinstance(signal_votes, list) or not signal_votes:
        return round(base, 4), {
            "method": "regime_fallback",
            "reason": "no_signal_votes",
            "base": base,
        }

    meta_scores = []
    weak_count = 0
    neutral_count = 0
    strong_count = 0

    for vote in signal_votes:
        if not isinstance(vote, dict):
            continue

        try:
            meta_scores.append(float(vote.get("meta_score", 0.0) or 0.0))
        except Exception:
            pass

        r = str(vote.get("momentum_regime", "unknown")).lower()
        if r == "weak":
            weak_count += 1
        elif r == "neutral":
            neutral_count += 1
        elif r in {"strong", "bullish", "high"}:
            strong_count += 1

    if not meta_scores:
        return round(base, 4), {
            "method": "regime_fallback",
            "reason": "no_valid_meta_scores",
            "base": base,
        }

    avg_meta = mean(meta_scores)
    max_meta = max(meta_scores)

    signal_component = clamp(avg_meta / 70.0, 0.0, 1.0) * 0.35
    max_bonus = 0.04 if max_meta >= 55 else 0.02 if max_meta >= 45 else 0.0
    weak_penalty = 0.03 if weak_count > neutral_count + strong_count else 0.0

    confidence = clamp(base + signal_component + max_bonus - weak_penalty, 0.35, 0.90)

    return round(confidence, 4), {
        "method": "regime_plus_signal_votes",
        "base": round(base, 4),
        "avg_meta_score": round(avg_meta, 4),
        "max_meta_score": round(max_meta, 4),
        "signal_component": round(signal_component, 4),
        "max_bonus": round(max_bonus, 4),
        "weak_penalty": round(weak_penalty, 4),
        "votes_count": len(meta_scores),
        "weak_count": weak_count,
        "neutral_count": neutral_count,
        "strong_count": strong_count,
    }


def export_crypto_to_portfolio_input(
    input_path: str = INPUT_PATH,
    trading_plan_path: str = TRADING_PLAN_PATH,
    portfolio_overview_path: str = PORTFOLIO_OVERVIEW_PATH,
    signal_votes_path: str = SIGNAL_VOTES_PATH,
    output_path: str = OUTPUT_PATH
):
    data = load_json(input_path)
    trading_plan = load_json(trading_plan_path)
    overview = load_json(portfolio_overview_path)
    signal_votes = load_json(signal_votes_path)

    regime = data.get("regime", "unknown")

    # Canonical portfolio weights are measured against deployable capital only.
    # Treasury is part of total virtual capital but is not trading capital.
    capital_pools = load_json("/opt/nsc/data/preprod/capital/capital_pools.json")
    capital_state = load_json("/opt/nsc/data/preprod/portfolio/capital_state.json")
    try:
        crypto_pool = float(
            (
                (
                    capital_pools.get("pools")
                    or {}
                ).get("crypto_exchange_pool")
                or {}
            ).get("total_eur")
            or 0.0
        )
        deployable_capital = float(
            capital_state.get("deployable_capital_eur")
            or 0.0
        )
        target_weight = (
            round(
                crypto_pool / deployable_capital,
                6,
            )
            if deployable_capital > 0
            else float(
                data.get("trading_ratio", 0.0)
                or 0.0
            )
        )
    except Exception:
        target_weight = float(
            data.get("trading_ratio", 0.0)
            or 0.0
        )

    confidence, confidence_details = compute_dynamic_crypto_confidence(regime, signal_votes)

    strategy_weights = data.get("strategy_weights", {})
    pockets = data.get("pockets", {})
    exposure_pct_total = float(overview.get("exposure_pct_total", 0.0) or 0.0)

    payload = {
        "brick": "crypto",
        "enabled": True,
        "portfolio_role": "alpha_aggressive",
        "signal_type": "allocation_proposal",
        "target_weight": target_weight,
        "confidence": confidence,
        "regime": regime,
        "allocation": strategy_weights,
        "drivers": {
            "regime": regime,
            "emotional_regime": data.get("emotional_regime", "unknown"),
            "action": data.get("action", "unknown"),
            "emotional_action": data.get("emotional_action", "unknown"),
            "trading_ratio": data.get("trading_ratio", 0.0),
            "max_positions": data.get("max_positions", 0),
            "capital_per_trade": data.get("capital_per_trade", 0.0),
            "confidence_details": confidence_details,
        },
        "risk_flags": {
            "current_exposure_pct_total": exposure_pct_total,
            "max_concurrent_positions": data.get("max_concurrent_positions", 0),
            "kill_switch_reference": trading_plan.get("risk_management", {}).get("kill_switch_trigger")
        },
        "inertia_profile": {
            "rebalance_frequency": "high",
            "max_weight_change_per_cycle": 0.06,
            "min_threshold_to_rebalance": 0.02
        },
        "capital_context": {
            "pockets": pockets,
            "trading_budget": data.get("trading_budget", 0.0),
            "total_budget": data.get("total_budget", 0.0),
            "total_capital": data.get("total_capital", 0.0)
        },
        "execution_mode": "signal_only",
        "funding_pool": "crypto_exchange_pool",
        "source_file": input_path,
        "confidence_source_file": signal_votes_path,
    }

    save_json(payload, output_path)
    return payload


if __name__ == "__main__":
    result = export_crypto_to_portfolio_input()
    print(result)
