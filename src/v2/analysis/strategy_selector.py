from pathlib import Path
from datetime import datetime, timezone
import json


DATA_DIR = Path("/opt/nsc/data/preprod")

PERF = (
    DATA_DIR
    / "analysis"
    / "strategy_performance.json"
)

OUT = (
    DATA_DIR
    / "analysis"
    / "strategy_weights.json"
)


# Strategies used by the crypto sizing layer.
#
# market_momentum is explicitly included because it is a distinct
# executable strategy in the current RC2 decision chain.
STRATEGIES = [
    "momentum",
    "market_momentum",
    "breakout",
    "whale",
    "sniper",
]


# Economic sample governance.
#
# < 10:
#   insufficient sample
#
# 10-29:
#   observation sample only
#
# >= 30:
#   selector may modulate strategy exposure
#
# >= 100:
#   statistically mature RC2 sample
MIN_ECONOMIC_EVENTS = 10
MIN_ACTIONABLE_ECONOMIC_EVENTS = 30
HIGH_CONFIDENCE_ECONOMIC_EVENTS = 100


def load_json(path, default):
    try:
        if (
            path.exists()
            and path.stat().st_size > 0
        ):
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
    except Exception:
        pass

    return default


def clamp(x, lo, hi):
    return max(
        lo,
        min(hi, x),
    )


def _safe_float(value, default=None):
    if value is None:
        return default

    try:
        return float(value)
    except Exception:
        return default


def _sample_state(
    economic_events: int,
):
    if economic_events < MIN_ECONOMIC_EVENTS:
        return (
            "insufficient",
            "insufficient_economic_sample",
        )

    if (
        economic_events
        < MIN_ACTIONABLE_ECONOMIC_EVENTS
    ):
        return (
            "observation",
            "economic_sample_observation_only",
        )

    if (
        economic_events
        >= HIGH_CONFIDENCE_ECONOMIC_EVENTS
    ):
        return (
            "high_confidence",
            "high_confidence_economic_sample",
        )

    return (
        "actionable",
        "actionable_economic_sample",
    )


def score_strategy(s):
    """
    Strategy Selector V2.

    Decision semantics are based only on economic exit-event
    performance produced by strategy_performance_engine_v3.

    Lifecycle event counts and legacy winrate/pnl_avg remain
    available for diagnostics but do not govern selection.

    Returns:
        score: float
        label: str
        reason: str
        context: dict
    """
    if not isinstance(s, dict):
        s = {}

    economic_events = int(
        s.get("economic_exit_events", 0)
        or 0
    )

    economic_winrate = _safe_float(
        s.get("economic_winrate"),
        None,
    )

    expectancy = _safe_float(
        s.get("expectancy"),
        None,
    )

    economic_pf = _safe_float(
        s.get(
            "economic_profit_factor",
            s.get("profit_factor"),
        ),
        None,
    )

    payoff_ratio = _safe_float(
        s.get("payoff_ratio"),
        None,
    )

    (
        sample_state,
        sample_reason,
    ) = _sample_state(
        economic_events
    )

    context = {
        "economic_exit_events": (
            economic_events
        ),
        "sample_state": sample_state,
        "economic_winrate": (
            economic_winrate
        ),
        "economic_profit_factor": (
            economic_pf
        ),
        "expectancy": expectancy,
        "payoff_ratio": payoff_ratio,
    }

    # ---------------------------------------------------------
    # Sample governance
    # ---------------------------------------------------------

    if sample_state == "insufficient":
        return (
            0.5,
            "neutral",
            sample_reason,
            context,
        )

    if sample_state == "observation":
        return (
            0.5,
            "neutral",
            sample_reason,
            context,
        )

    # ---------------------------------------------------------
    # Economic integrity gates
    # ---------------------------------------------------------

    # Profit factor cannot be established when no losing
    # economic exits have yet been observed.
    #
    # Even with positive expectancy, V2 refuses to boost an
    # incomplete one-sided sample.
    if economic_pf is None:
        return (
            0.5,
            "neutral",
            "profit_factor_not_established",
            context,
        )

    # Strong negative economic evidence.
    #
    # A strategy with both:
    # - PF < 1
    # - negative expectancy
    #
    # is destroying value over its realized economic exits.
    if (
        economic_pf < 1.0
        and expectancy is not None
        and expectancy < 0
    ):
        # Score remains diagnostic.
        pf_score = clamp(
            economic_pf / 1.0,
            0.0,
            1.0,
        )

        win_score = clamp(
            economic_winrate
            if economic_winrate is not None
            else 0.0,
            0.0,
            1.0,
        )

        payoff_score = clamp(
            payoff_ratio
            if payoff_ratio is not None
            else 0.0,
            0.0,
            1.0,
        )

        score = (
            0.45 * pf_score
            + 0.30 * win_score
            + 0.25 * payoff_score
        )

        return (
            round(score, 4),
            "reduce",
            "negative_economic_expectancy_and_pf_below_one",
            context,
        )

    # ---------------------------------------------------------
    # Positive economic evidence
    # ---------------------------------------------------------

    # Boost requires coherent realized profitability.
    #
    # We deliberately require both:
    # - PF > 1
    # - positive expectancy
    #
    # so a high hit-rate alone can never trigger a boost.
    if (
        economic_pf > 1.0
        and expectancy is not None
        and expectancy > 0
    ):
        pf_score = clamp(
            (economic_pf - 1.0) / 1.0,
            0.0,
            1.0,
        )

        win_score = clamp(
            economic_winrate
            if economic_winrate is not None
            else 0.0,
            0.0,
            1.0,
        )

        payoff_score = clamp(
            payoff_ratio
            if payoff_ratio is not None
            else 0.0,
            0.0,
            1.0,
        )

        score = (
            0.45 * win_score
            + 0.35 * pf_score
            + 0.20 * payoff_score
        )

        if score >= 0.60:
            return (
                round(score, 4),
                "boost",
                "positive_economic_performance",
                context,
            )

        return (
            round(score, 4),
            "neutral",
            "positive_but_not_strong_enough",
            context,
        )

    # ---------------------------------------------------------
    # Mixed / inconclusive evidence
    # ---------------------------------------------------------

    return (
        0.5,
        "neutral",
        "mixed_economic_evidence",
        context,
    )


def weight_from_label(label):
    """
    Output contract.

    Position sizing independently clamps selector weights to
    [0.75, 1.05], so this module remains subordinate to the
    Risk Engine and strategy intensity controls.
    """
    if label == "boost":
        return 1.05

    if label == "reduce":
        return 0.75

    return 1.0


def main():
    perf = load_json(
        PERF,
        {},
    )

    by_strategy = (
        perf.get("by_strategy", {})
        if isinstance(perf, dict)
        else {}
    )

    weights = {}
    diagnostics = {}

    for strat in STRATEGIES:
        s = by_strategy.get(
            strat,
            {},
        )

        (
            score,
            label,
            reason,
            context,
        ) = score_strategy(s)

        weights[strat] = (
            weight_from_label(label)
        )

        diagnostics[strat] = {
            "score": score,
            "label": label,
            "reason": reason,

            # V2 economic decision metrics.
            "economic_exit_events": (
                context.get(
                    "economic_exit_events"
                )
            ),
            "sample_state": context.get(
                "sample_state"
            ),
            "economic_winrate": (
                context.get(
                    "economic_winrate"
                )
            ),
            "economic_profit_factor": (
                context.get(
                    "economic_profit_factor"
                )
            ),
            "expectancy": context.get(
                "expectancy"
            ),
            "payoff_ratio": context.get(
                "payoff_ratio"
            ),

            # Legacy metrics retained strictly for audit
            # compatibility and explainability.
            "legacy": {
                "trades": s.get(
                    "trades",
                    0,
                ),
                "lifecycle_events": s.get(
                    "lifecycle_events",
                    0,
                ),
                "winrate": s.get(
                    "winrate"
                ),
                "pnl_avg": s.get(
                    "pnl_avg"
                ),
                "profit_factor": s.get(
                    "profit_factor"
                ),
            },
        }

    payload = {
        "ts": (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "engine": "strategy_selector_v2",
        "semantics_version": (
            "v2_economic_performance_governance"
        ),
        "mode": (
            "economic_exit_event_strategy_modulation"
        ),
        "sample_thresholds": {
            "min_economic_events": (
                MIN_ECONOMIC_EVENTS
            ),
            "min_actionable_economic_events": (
                MIN_ACTIONABLE_ECONOMIC_EVENTS
            ),
            "high_confidence_economic_events": (
                HIGH_CONFIDENCE_ECONOMIC_EVENTS
            ),
        },
        "weight_contract": {
            "boost": 1.05,
            "neutral": 1.0,
            "reduce": 0.75,
            "position_sizing_clamp": [
                0.75,
                1.05,
            ],
        },
        "weights": weights,
        "diagnostics": diagnostics,
        "source": str(PERF),
        "source_engine": (
            perf.get("engine")
            if isinstance(perf, dict)
            else None
        ),
        "source_semantics_version": (
            perf.get("semantics_version")
            if isinstance(perf, dict)
            else None
        ),
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
