from options_data_adapter_v3 import (
    OptionsDataAdapterError,
    adapt_expiration_input_v3,
    adapt_greeks_input_v3,
    adapt_sizing_input_v3,
)
from options_greeks_engine_v3 import calculate_option_greeks_v3
from options_contract_sizing_v3 import calculate_contract_quantity_v3
from options_expiration_policy_v3 import select_expiration_v3

#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone
from options_portfolio_engine_v3 import allocate_portfolio
from options_position_manager_v3 import update_positions
from providers.yfinance_option_chain_provider_v3 import fetch_normalized_option_chain
from options_contract_selector_v3 import ContractSelectionError, select_contract_structure_v3

OUT = Path("/opt/nsc/data/preprod/options_v3")
OUT.mkdir(parents=True, exist_ok=True)

SRC = Path("/opt/nsc/app/src/v2")
PATHS = {
    # RC2 canonical live inputs.
    "offensive_execution": Path(
        "/opt/nsc/data/preprod/equities_offensive/risk/"
        "execution_candidates.json"
    ),
    "defensive_state": Path(
        "/opt/nsc/data/preprod/defensive/defensive_state.json"
    ),

    # Transitional analytical dependencies retained by Options V3.
    #
    # IMPORTANT RC2 CONTRACT:
    # V2 volatility_context is intentionally NOT a runtime decision input.
    # Its IV Rank values originate from legacy sandbox/bootstrap data and
    # have no certified external market provenance.
}

def enrich_candidate_capabilities_v3(
    candidate: dict,
    risk_context: dict,
    valuation_timestamp=None,
) -> dict:
    enriched = dict(candidate)

    try:
        expiration_input = adapt_expiration_input_v3(
            enriched,
            valuation_timestamp=valuation_timestamp,
        )

        expiration_decision = select_expiration_v3(
            expirations=[expiration_input.expiration],
            current_timestamp=(
                expiration_input.valuation_timestamp
            ),
        )

        if hasattr(expiration_decision, "to_dict"):
            expiration_payload = expiration_decision.to_dict()
        elif hasattr(expiration_decision, "__dict__"):
            expiration_payload = dict(expiration_decision.__dict__)
        elif isinstance(expiration_decision, dict):
            expiration_payload = dict(expiration_decision)
        else:
            expiration_payload = {"decision": str(expiration_decision)}

        enriched["expiration_policy"] = expiration_payload

        greeks_input = adapt_greeks_input_v3(
            enriched,
            valuation_timestamp=valuation_timestamp,
        )

        greeks = calculate_option_greeks_v3(
            underlying_price=greeks_input.underlying_price,
            strike_price=greeks_input.strike_price,
            time_to_expiry_years=greeks_input.time_to_expiry_years,
            risk_free_rate=0.0,  # temporary SHADOW assumption
            volatility=greeks_input.volatility,
            option_type=greeks_input.option_type,
        )

        if hasattr(greeks, "to_dict"):
            greeks_payload = greeks.to_dict()
        elif hasattr(greeks, "__dict__"):
            greeks_payload = dict(greeks.__dict__)
        else:
            greeks_payload = dict(greeks)

        enriched["greeks"] = greeks_payload
        enriched["delta"] = greeks_payload.get("delta")
        enriched["gamma"] = greeks_payload.get("gamma")
        enriched["theta"] = greeks_payload.get("theta")
        enriched["vega"] = greeks_payload.get("vega")

        sizing_input = adapt_sizing_input_v3(
            enriched,
            risk_context,
        )

        sizing_kwargs = sizing_input.to_dict()

        if enriched.get("strategy") == "covered_call":
            underlying_quantity = enriched.get(
                "underlying_equity_quantity"
            )

            try:
                underlying_quantity = int(
                    float(underlying_quantity or 0)
                )
            except (TypeError, ValueError):
                underlying_quantity = 0

            covered_contract_capacity = (
                underlying_quantity // 100
            )

            if covered_contract_capacity <= 0:
                raise OptionsDataAdapterError(
                    "covered_call: insufficient underlying shares"
                )

            sizing_payload = {
                "contract_quantity": covered_contract_capacity,
                "estimated_risk_eur": float(
                    enriched.get("estimated_risk_eur") or 0.0
                ),
                "risk_budget_eur": float(
                    sizing_input.max_trade_risk_eur
                ),
                "maximum_loss_per_contract": None,
                "contract_multiplier": (
                    sizing_input.contract_multiplier
                ),
                "sizing_reason": (
                    "covered_call_capacity_from_existing_equity"
                ),
                "sizing_valid": True,
                "underlying_equity_quantity": (
                    underlying_quantity
                ),
                "covered_contract_capacity": (
                    covered_contract_capacity
                ),
            }

        else:
            sizing = calculate_contract_quantity_v3(
                **sizing_kwargs
            )

            if hasattr(sizing, "to_dict"):
                sizing_payload = sizing.to_dict()
            elif hasattr(sizing, "__dict__"):
                sizing_payload = dict(sizing.__dict__)
            else:
                sizing_payload = dict(sizing)

        quantity = int(
            sizing_payload.get(
                "contract_quantity",
                sizing_payload.get("quantity", 0),
            )
            or 0
        )

        if quantity <= 0:
            raise OptionsDataAdapterError(
                "contract_sizing: zero contract quantity"
            )

        enriched["contract_sizing"] = sizing_payload
        enriched["contract_quantity"] = quantity

        # Preserve the pre-sizing estimate for audit/explainability, but
        # promote the post-sizing risk as the canonical downstream risk.
        #
        # Downstream consumers (validation, decisions, ranking, portfolio
        # allocation and position lifecycle) use estimated_risk_eur.
        # Therefore it must represent the executable/sized contract risk,
        # not the coarse upstream strategy estimate.
        pre_sizing_estimated_risk_eur = enriched.get(
            "estimated_risk_eur"
        )
        sized_estimated_risk_eur = sizing_payload.get(
            "estimated_risk_eur"
        )

        enriched["pre_sizing_estimated_risk_eur"] = (
            pre_sizing_estimated_risk_eur
        )
        enriched["sized_estimated_risk_eur"] = (
            sized_estimated_risk_eur
        )

        if sized_estimated_risk_eur is not None:
            enriched["estimated_risk_eur"] = float(
                sized_estimated_risk_eur
            )

        enriched["premium_per_contract"] = (
            sizing_input.premium_per_contract
        )
        enriched["contract_multiplier"] = (
            sizing_input.contract_multiplier
        )
        enriched["expiration"] = expiration_input.expiration
        enriched["days_to_expiry"] = (
            expiration_input.days_to_expiry
        )
        enriched["capability_adapter_version"] = "options_v3_adapter_v1"
        enriched["capability_enrichment_status"] = "complete"
        enriched["execution_mode"] = "SIMULATED_ONLY"
        enriched["real_execution_allowed"] = False
        return enriched

    except OptionsDataAdapterError as exc:
        enriched["capability_enrichment_status"] = "rejected"
        enriched["capability_rejection_reason"] = str(exc)
        enriched["contract_quantity"] = 0
        enriched["execution_mode"] = "SIMULATED_ONLY"
        enriched["real_execution_allowed"] = False
        return enriched



OPTIONS_V3_OPTION_CHAIN_CACHE_DIR = Path(
    "/opt/nsc/data/preprod/options_v3/option_chain_cache"
)

OPTIONS_V3_STRATEGY_TARGET_DTE = {
    "covered_call": 30,
    "cash_secured_put": 30,
    "bull_call_spread": 45,
    "bear_put_spread": 45,
    "neutral_spread": 30,
    "long_call": 45,
    "bull_put_spread": 30,
}

OPTIONS_V3_DEFERRED_STRATEGIES = {
    "bear_call_spread": (
        "DEFERRED_NOT_RUNTIME_SUPPORTED"
    ),
}

OPTIONS_V3_MINIMUM_DTE = 7
OPTIONS_V3_MAXIMUM_DTE = 90
OPTIONS_V3_PROVIDER_CACHE_MAXIMUM_AGE_MINUTES = 60


def enrich_candidate_contract_selection_v3(
    candidate,
    option_chain_cycle_cache,
):
    """
    Enrich a simulated Options V3 candidate with a real option structure.

    The provider is used for read-only market data. No broker operation is
    performed. Missing, unsupported or invalid data fails closed.
    """
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a dictionary")

    ticker = str(candidate.get("ticker") or "").strip().upper()
    strategy = str(candidate.get("strategy") or "").strip().lower()

    if not ticker:
        raise ValueError("missing_ticker")

    if strategy not in OPTIONS_V3_STRATEGY_TARGET_DTE:
        raise ValueError(
            f"unsupported_strategy:{strategy or 'missing'}"
        )

    target_dte = OPTIONS_V3_STRATEGY_TARGET_DTE[strategy]

    cache_key = (
        ticker,
        target_dte,
        OPTIONS_V3_MINIMUM_DTE,
        OPTIONS_V3_MAXIMUM_DTE,
    )

    if cache_key in option_chain_cycle_cache:
        provider_payload = option_chain_cycle_cache[cache_key]
        cycle_cache_status = "IN_MEMORY_CYCLE_CACHE"

    else:
        provider_payload = fetch_normalized_option_chain(
            ticker,
            target_dte=target_dte,
            minimum_dte=OPTIONS_V3_MINIMUM_DTE,
            maximum_dte=OPTIONS_V3_MAXIMUM_DTE,
            cache_dir=OPTIONS_V3_OPTION_CHAIN_CACHE_DIR,
            cache_maximum_age_minutes=(
                OPTIONS_V3_PROVIDER_CACHE_MAXIMUM_AGE_MINUTES
            ),
            force_refresh=False,
        )

        if not isinstance(provider_payload, dict):
            raise ValueError(
                "provider_payload_not_dictionary"
            )

        contracts = provider_payload.get("contracts")

        if not isinstance(contracts, list) or not contracts:
            raise ValueError(
                "provider_returned_no_valid_contracts"
            )

        option_chain_cycle_cache[cache_key] = provider_payload

        metadata = provider_payload.get("metadata", {})

        if not isinstance(metadata, dict):
            metadata = {}

        cycle_cache_status = str(
            metadata.get(
                "cache_status",
                "LIVE_OR_PERSISTENT_CACHE",
            )
        )

    try:
        selected_structure = select_contract_structure_v3(
            strategy=strategy,
            provider_payload=provider_payload,
        )

    except ContractSelectionError:
        raise

    except Exception as exc:
        raise ContractSelectionError(
            f"unexpected_selector_error:"
            f"{type(exc).__name__}:{exc}"
        ) from exc

    if not isinstance(selected_structure, dict):
        raise ContractSelectionError(
            "selected_structure_not_dictionary"
        )

    if selected_structure.get("selection_status") != "SELECTED":
        raise ContractSelectionError(
            "selection_status_not_selected"
        )

    if selected_structure.get("simulation_only") is not True:
        raise ContractSelectionError(
            "simulation_only_not_enforced"
        )

    if selected_structure.get("real_execution_allowed") is not False:
        raise ContractSelectionError(
            "real_execution_not_forbidden"
        )

    contract_legs = selected_structure.get("contract_legs")

    if not isinstance(contract_legs, list) or not contract_legs:
        raise ContractSelectionError(
            "selected_structure_has_no_contract_legs"
        )

    primary_leg = contract_legs[0]

    if not isinstance(primary_leg, dict):
        raise ContractSelectionError(
            "primary_leg_not_dictionary"
        )

    net_premium = selected_structure.get(
        "net_premium_per_share"
    )

    try:
        normalized_premium = abs(float(net_premium))

    except (TypeError, ValueError) as exc:
        raise ContractSelectionError(
            "invalid_net_premium_per_share"
        ) from exc

    if normalized_premium <= 0:
        raise ContractSelectionError(
            "non_positive_normalized_premium"
        )

    merged_candidate = dict(candidate)

    merged_candidate.update({
        "provider": selected_structure.get("provider"),
        "provider_timestamp": selected_structure.get(
            "provider_timestamp"
        ),
        "provider_cache_status": cycle_cache_status,
        "expiration": selected_structure.get("expiration"),
        "days_to_expiry": selected_structure.get(
            "days_to_expiry"
        ),
        "target_dte": target_dte,
        "underlying_price": selected_structure.get(
            "underlying_price"
        ),
        "contract_legs": contract_legs,
        "contract_leg_count": len(contract_legs),
        "net_premium_per_share": net_premium,
        "gross_debit_per_share": selected_structure.get(
            "gross_debit_per_share"
        ),
        "gross_credit_per_share": selected_structure.get(
            "gross_credit_per_share"
        ),
        "spread_width": selected_structure.get(
            "spread_width"
        ),
        "maximum_loss_per_contract": selected_structure.get(
            "maximum_loss_per_contract"
        ),
        "maximum_profit_per_contract": selected_structure.get(
            "maximum_profit_per_contract"
        ),
        "assignment_notional_per_contract": (
            selected_structure.get(
                "assignment_notional_per_contract"
            )
        ),
        "selection_status": "SELECTED",
        "simulation_only": True,
        "real_execution_allowed": False,

        # Canonical inputs required by the capability adapters.
        "strike_price": primary_leg.get("strike"),
        "strike": primary_leg.get("strike"),
        "option_type": primary_leg.get("option_type"),
        "implied_volatility": primary_leg.get(
            "implied_volatility"
        ),
        "volatility": primary_leg.get(
            "implied_volatility"
        ),
        "bid": primary_leg.get("bid"),
        "ask": primary_leg.get("ask"),
        "mid": primary_leg.get("mid"),
        "premium": normalized_premium,
        "premium_per_share": normalized_premium,
        "premium_per_contract": normalized_premium,
        "contract_symbol": primary_leg.get(
            "contract_symbol"
        ),
        "contract_size": 100,
        "contract_multiplier": 100,
    })

    existing_explain = merged_candidate.get("explain")

    if not isinstance(existing_explain, list):
        existing_explain = []

    merged_candidate["explain"] = [
        *existing_explain,
        f"provider={selected_structure.get('provider')}",
        f"expiration={selected_structure.get('expiration')}",
        f"days_to_expiry={selected_structure.get('days_to_expiry')}",
        f"contract_legs={len(contract_legs)}",
        f"provider_cache_status={cycle_cache_status}",
        "execution_mode=SIMULATION_ONLY",
    ]

    return merged_candidate

def now():
    return datetime.now(timezone.utc).isoformat()

def load(path, default):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return default

def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2))

def build_live_offensive_signals(document):
    """
    Convert the canonical Offensive Equities execution contract into
    Options V3 directional signals.

    Only risk-approved execution candidates are accepted. Market price is
    deliberately not copied into the signal: the Options V3 provider owns
    the canonical underlying market price during contract selection.
    """
    if not isinstance(document, dict):
        return []

    candidates = document.get("candidates", [])
    if not isinstance(candidates, list):
        return []

    direction_map = {
        "long": "bullish",
        "short": "bearish",
        "bullish": "bullish",
        "bearish": "bearish",
    }

    signals = []

    for item in candidates:
        if not isinstance(item, dict):
            continue

        if item.get("allowed") is not True:
            continue

        ticker = str(
            item.get("symbol") or item.get("ticker") or ""
        ).strip().upper()

        if not ticker:
            continue

        direction = direction_map.get(
            str(item.get("direction") or "").strip().lower(),
            "neutral",
        )

        raw_score = item.get("meta_score")

        try:
            confidence = float(raw_score) / 100.0
        except (TypeError, ValueError):
            confidence = 0.5

        confidence = max(0.0, min(1.0, confidence))

        signals.append({
            "ticker": ticker,
            "signal_type": "offensive_runtime",
            "direction": direction,
            "confidence": confidence,
            "setup": item.get("setup"),
            "source": "equities_offensive_execution_candidates",
            "source_ts": item.get("ts"),
            "source_meta_score": raw_score,
            "source_allowed": True,
            "source_engine": item.get("engine"),
            "source_regime": item.get("regime"),
        })

    return signals


def build_live_covered_call_signals(document):
    """
    Convert canonical Defensive Equity positions into covered-call
    overlays only where at least one standard 100-share contract is
    actually covered.

    Fractional simulated equity positions therefore cannot manufacture
    covered-call capacity.
    """
    if not isinstance(document, dict):
        return []

    positions = document.get("positions", [])
    if not isinstance(positions, list):
        return []

    signals = []

    for position in positions:
        if not isinstance(position, dict):
            continue

        if str(position.get("type") or "").lower() != "stock":
            continue

        ticker = str(
            position.get("symbol") or position.get("ticker") or ""
        ).strip().upper()

        if not ticker:
            continue

        try:
            quantity = float(position.get("qty") or 0.0)
        except (TypeError, ValueError):
            continue

        covered_contract_capacity = int(quantity // 100)

        if covered_contract_capacity <= 0:
            continue

        signals.append({
            "ticker": ticker,
            "signal_type": "existing_equity_overlay",
            "direction": "neutral",
            "confidence": 0.65,
            "setup": "covered_call_candidate",
            "underlying_equity_quantity": quantity,
            "covered_contract_capacity":
                covered_contract_capacity,
            "source": "defensive_state",
            "source_ts": document.get("generated_at"),
            "source_position_price":
                position.get("price"),
        })

    return signals


IV_RANK_STATUS_UNAVAILABLE = "UNAVAILABLE_INSUFFICIENT_HISTORY"
IV_PERCENTILE_STATUS_UNAVAILABLE = "UNAVAILABLE_INSUFFICIENT_HISTORY"
IV_PROVENANCE_STATUS = "NO_CERTIFIED_HISTORICAL_PROVENANCE"


def choose_strategy(signal):
    """
    Choose only strategies that are demonstrable with certified RC2 inputs.

    IV Rank and IV Percentile are unavailable until sufficient comparable
    provider-backed history exists. Strategies whose selection depends on
    IV Rank therefore fail closed instead of silently treating missing data
    as zero or inheriting legacy V1/V2 sandbox values.
    """
    direction = signal.get("direction", "neutral")
    signal_type = signal.get("signal_type", "")

    if direction == "bearish":
        return (
            "bear_put_spread",
            "hedge",
            "unknown",
            "SELECTED",
            None,
        )

    if direction in ["bullish", "strong_bullish"]:
        return (
            None,
            "alpha",
            "unknown",
            "REJECTED",
            "iv_rank_unavailable_for_strategy_selection",
        )

    if direction == "neutral_to_bullish":
        return (
            None,
            "entry_yield",
            "unknown",
            "REJECTED",
            "iv_rank_unavailable_for_strategy_selection",
        )

    if signal_type == "existing_equity_overlay":
        return (
            "covered_call",
            "yield",
            "unknown",
            "SELECTED",
            None,
        )

    return (
        "neutral_spread",
        "neutral",
        "unknown",
        "SELECTED",
        None,
    )


def estimate_risk(strategy, spot):
    spot = float(spot or 0)
    if strategy in ["bull_call_spread", "bear_put_spread"]:
        return round(max(spot * 1.5, 500), 2)
    if strategy == "long_call":
        return round(max(spot * 0.8, 250), 2)
    if strategy == "cash_secured_put":
        return round(max(spot * 95, 1000), 2)
    if strategy == "covered_call":
        return round(max(spot * 0.5, 100), 2)
    return round(max(spot * 1.0, 300), 2)

def build_candidate(signal):
    ticker = signal.get("ticker")

    (
        strategy,
        role,
        vol_regime,
        strategy_selection_status,
        strategy_selection_reason,
    ) = choose_strategy(signal)

    confidence = float(
        signal.get("confidence") or 0.5
    )
    spot = float(
        signal.get("spot") or 0
    )

    if strategy is None:
        risk = 0.0
        score = None
    else:
        risk = estimate_risk(
            strategy,
            spot,
        )
        score = round(
            confidence * 60
            + (
                10
                if role in ["alpha", "hedge"]
                else 5
            ),
            2,
        )

    return {
        "ts": now(),
        "ticker": ticker,
        "strategy": strategy,
        "direction": signal.get(
            "direction",
            "neutral",
        ),
        "role": role,
        "score": score,
        "confidence": confidence,
        "estimated_risk_eur": risk,
        "vol_regime": vol_regime,

        # RC2 volatility provenance contract.
        "iv_rank": None,
        "iv_rank_status": IV_RANK_STATUS_UNAVAILABLE,
        "iv_percentile": None,
        "iv_percentile_status": (
            IV_PERCENTILE_STATUS_UNAVAILABLE
        ),
        "iv_provenance_status": (
            IV_PROVENANCE_STATUS
        ),

        "strategy_selection_status": (
            strategy_selection_status
        ),
        "strategy_selection_reason": (
            strategy_selection_reason
        ),

        "source_signal": signal,
        "underlying_equity_quantity": signal.get(
            "underlying_equity_quantity"
        ),
        "explain": [
            f"direction={signal.get('direction')}",
            f"strategy={strategy}",
            f"role={role}",
            f"vol_regime={vol_regime}",
            (
                "iv_rank="
                "UNAVAILABLE_INSUFFICIENT_HISTORY"
            ),
            (
                "iv_percentile="
                "UNAVAILABLE_INSUFFICIENT_HISTORY"
            ),
            (
                "strategy_selection_status="
                f"{strategy_selection_status}"
            ),
        ],
    }

def validate(candidate):
    if not candidate.get("ticker"):
        return False, "missing_ticker"

    if (
        candidate.get("strategy_selection_status")
        != "SELECTED"
    ):
        return False, (
            candidate.get("strategy_selection_reason")
            or "strategy_selection_not_selected"
        )

    if not candidate.get("strategy"):
        return False, "missing_strategy"

    score = candidate.get("score")

    if score is None:
        return False, "score_unavailable"

    try:
        score = float(score)
    except (TypeError, ValueError):
        return False, "invalid_score"

    if score < 55:
        return False, "score_below_threshold"

    estimated_risk_eur = candidate.get(
        "estimated_risk_eur"
    )

    if estimated_risk_eur is None:
        return False, "estimated_risk_unavailable"

    try:
        estimated_risk_eur = float(
            estimated_risk_eur
        )
    except (TypeError, ValueError):
        return False, "invalid_estimated_risk"

    if estimated_risk_eur > 2000:
        return False, "risk_above_limit"

    return True, "approved"

def main():
    open_positions = []
    closed_positions = []
    print("===== OPTIONS V3 AUTONOMOUS SHADOW RUN =====")

    offensive_execution = load(
        PATHS["offensive_execution"],
        {},
    )
    defensive_state = load(
        PATHS["defensive_state"],
        {},
    )

    offensive_signals = build_live_offensive_signals(
        offensive_execution
    )
    overlay_signals = build_live_covered_call_signals(
        defensive_state
    )

    all_signals = offensive_signals + overlay_signals

    candidates_raw = [
        build_candidate(s)
        for s in all_signals
    ]

    candidates_validated = []
    decisions = []
    option_chain_cycle_cache = {}

    pockets_doc = load(
        Path("/opt/nsc/data/preprod/portfolio/pockets.json"),
        {},
    )
    pockets = (
        pockets_doc.get("pockets", {})
        if isinstance(pockets_doc, dict)
        else {}
    )
    options_pocket = (
        pockets.get("options_us", {})
        if isinstance(pockets, dict)
        else {}
    )
    options_capital_eur = float(
        options_pocket.get("budget_eur", 0.0) or 0.0
    )

    if options_capital_eur <= 0:
        raise RuntimeError(
            "options_us pocket budget is missing or zero"
        )

    options_max_total_risk_eur = (
        options_capital_eur * 0.50
    )
    options_max_trade_risk_eur = (
        options_capital_eur * 0.20
    )

    for c in candidates_raw:
        contract_selection_error = None

        if (
            c.get("strategy_selection_status")
            != "SELECTED"
        ):
            ok = False
            reason = (
                c.get("strategy_selection_reason")
                or "strategy_selection_failed"
            )

        else:
            try:
                c = enrich_candidate_contract_selection_v3(
                    c,
                    option_chain_cycle_cache,
                )

            except Exception as exc:
                contract_selection_error = (
                    f"contract_selection_failed:"
                    f"{type(exc).__name__}:{exc}"
                )

            if contract_selection_error:
                ok = False
                reason = contract_selection_error

            else:
                c = enrich_candidate_capabilities_v3(
                    c,
                    risk_context={
                        "internal_available_risk_eur":
                            options_max_total_risk_eur,
                        "internal_max_trade_risk_eur":
                            options_max_trade_risk_eur,
                    },
                )

                if (
                    c.get("capability_enrichment_status")
                    != "complete"
                ):
                    ok = False
                    reason = c.get(
                        "capability_rejection_reason",
                        (
                            "options_v3_"
                            "capability_enrichment_failed"
                        ),
                    )

                else:
                    ok, reason = validate(c)
        decision = {
            "ts": now(),
            "ticker": c.get("ticker"),
            "strategy": c.get("strategy"),
            "status": "APPROVED" if ok else "REJECTED",
            "reason": reason,
            "score": c.get("score"),
            "estimated_risk_eur": c.get("estimated_risk_eur"),
            "role": c.get("role"),
            "strategy_selection_status": c.get(
                "strategy_selection_status"
            ),
            "strategy_selection_reason": c.get(
                "strategy_selection_reason"
            ),
            "iv_rank": c.get("iv_rank"),
            "iv_rank_status": c.get(
                "iv_rank_status"
            ),
            "iv_percentile": c.get(
                "iv_percentile"
            ),
            "iv_percentile_status": c.get(
                "iv_percentile_status"
            ),
            "iv_provenance_status": c.get(
                "iv_provenance_status"
            ),
        }
        decisions.append(decision)
        if ok:
            candidates_validated.append(c)

    # Options V3 operates inside the dedicated NSC options_us pocket.
    pockets_doc = load(
        Path("/opt/nsc/data/preprod/portfolio/pockets.json"),
        {},
    )
    pockets = (
        pockets_doc.get("pockets", {})
        if isinstance(pockets_doc, dict)
        else {}
    )
    options_pocket = (
        pockets.get("options_us", {})
        if isinstance(pockets, dict)
        else {}
    )
    options_capital_eur = float(
        options_pocket.get("budget_eur", 0.0) or 0.0
    )

    if options_capital_eur <= 0:
        raise RuntimeError(
            "options_us pocket budget is missing or zero"
        )

    portfolio = allocate_portfolio(
        candidates_validated,
        capital_eur=options_capital_eur,
        max_total_options_exposure_pct=0.50,
        max_trade_risk_pct=0.20,
    )


    # ===== FORCE POSITIONS FROM FILES =====
    open_positions = load("options_v3_positions.json", [])
    closed_positions = load("options_v3_positions_closed.json", [])
    # ===== END FORCE =====

    infrastructure_failure_reasons = [
        d.get("reason", "")
        for d in decisions
        if isinstance(d, dict)
        and (
            "OptionChainUnavailableError" in str(d.get("reason", ""))
            or "DataSource" in str(d.get("reason", ""))
            or "ProviderUnavailable" in str(d.get("reason", ""))
        )
    ]

    pipeline_status = (
        "degraded"
        if infrastructure_failure_reasons
        else "ok"
    )

    opportunity_status = (
        "DATA_SOURCE_FAILURE"
        if infrastructure_failure_reasons
        else (
            "ACTIVE_SELECTION"
            if candidates_validated
            else "NO_CURRENT_OPPORTUNITY"
        )
    )

    dashboard = {

        "ts": now(),
        "engine": "options_v3_autonomous_shadow",
        "module": "options_v3",
        "status": {
            "pipeline_status": pipeline_status,
            "mode": "SHADOW",
            "opportunity_status": opportunity_status,
            "infrastructure_failure_count": len(
                infrastructure_failure_reasons
            ),
        },
        "kpis": {
            "signals_total": len(all_signals),
            "candidates_raw": len(candidates_raw),
            "candidates_validated": len(candidates_validated),
            "decisions_total": len(decisions),
            "approved_count": len([d for d in decisions if d["status"] == "APPROVED"]),
            "rejected_count": len([d for d in decisions if d["status"] == "REJECTED"]),
        },
        "decisions": decisions,
        "positions": {
            "open": len(load("options_v3_positions.json", [])),
            "closed": len(load("options_v3_positions_closed.json", []))
        },
        "portfolio": {
            "pocket": "options_us",
            "capital_source": (
                "/opt/nsc/data/preprod/portfolio/pockets.json"
            ),
            "capital_eur": portfolio.get("capital_eur", 0),
            "selected_count": portfolio.get("selected_count", 0),
            "rejected_count": portfolio.get("rejected_count", 0),
            "used_risk_eur": portfolio.get("used_risk_eur", 0),
            "used_risk_pct": portfolio.get("used_risk_pct", 0),
            "max_total_risk_eur": portfolio.get(
                "max_total_risk_eur", 0
            ),
            "max_trade_risk_eur": portfolio.get(
                "max_trade_risk_eur", 0
            ),
        },
        "conclusion": "Options V3 autonomous shadow generated candidates from native options inputs.",
    }

    save("options_v3_candidates_raw.json", candidates_raw)
    save("options_v3_portfolio.json", portfolio)
    save("options_v3_portfolio_selected.json", portfolio.get("selected", []))
    save("options_v3_portfolio_rejected.json", portfolio.get("rejected", []))

    open_positions, closed_positions = update_positions()


    save("options_v3_candidates_validated.json", candidates_validated)
    save("options_v3_decisions.json", decisions)
    # ===== DASHBOARD POSITIONS POST-WRITE FIX =====
    open_positions_file = load(OUT / "options_v3_positions.json", [])
    closed_positions_file = load(OUT / "options_v3_positions_closed.json", [])

    dashboard["positions"] = {
        "open": len(open_positions_file),
        "closed": len(closed_positions_file),
    }

    save("options_v3_dashboard.json", dashboard)

    status_payload = {
        "status": "ok",
        "health": {
            "dashboard_artifact": True,
            "positions_artifact": True,
            "portfolio_artifact": True,
        },
        "mode": "SHADOW",
        "execution_allowed": False,
        "real_money_enabled": False,
        "action_policy": "SIMULATED_ONLY",
        "engine": "options_v3_autonomous_shadow",
        "env": "PREPROD",
        "portfolio_role": "active_options",
        "funding_pool": "ibkr_pool",
        "updated_at": now(),
    }

    save("options_v3_status.json", status_payload)

    # Backward-compatible API / monitoring files
    save("signals_raw.json", candidates_raw)
    save("signals_validated.json", candidates_validated)
    save(
        "signals_rejected.json",
        [d for d in decisions if d["status"] == "REJECTED"],
    )
    save("positions_open.json", open_positions_file)
    save("positions_closed.json", closed_positions_file)

    print(f"signals_total={len(all_signals)}")
    print(f"candidates_raw={len(candidates_raw)}")
    print(f"candidates_validated={len(candidates_validated)}")
    print("===== OPTIONS V3 AUTONOMOUS SHADOW DONE =====")

if __name__ == "__main__":
    main()
