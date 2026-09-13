from options_data_adapter_v3 import (
    OptionsDataAdapterError,
    adapt_expiration_input_v3,
    adapt_greeks_input_v3,
    adapt_sizing_input_v3,
)
from options_greeks_engine_v3 import calculate_option_greeks_v3
from options_risk_free_rate_runtime_v3 import (
    fetch_certified_risk_free_rate_network_v3,
)
from options_contract_sizing_v3 import calculate_contract_quantity_v3
from src.v2.core.fx import FXService, FXServiceError
from options_expiration_policy_v3 import select_expiration_v3

#!/usr/bin/env python3
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from options_portfolio_engine_v3 import allocate_portfolio
from options_performance_v3 import (
    build_options_performance_v3,
)
from options_position_manager_v3 import (
    calculate_open_risk_v3,
    open_selected_positions_v3,
    reconcile_existing_positions_v3,
)
from providers.yfinance_option_chain_provider_v3 import (
    OptionChainProviderError,
    fetch_normalized_option_chain,
    fetch_position_contract_quotes_v3,
)
from options_position_valuation_v3 import (
    OptionsPositionValuationError,
    value_open_position_v3,
)
from options_cycle_ledger_v3 import (
    append_cycle_ledger_entry_v3,
    build_cycle_ledger_entry_v3,
)
from options_iv_history_v3 import (
    IVObservationError,
    observe_and_update_iv_history,
)
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
    *,
    risk_free_rate,
    risk_free_rate_provenance,
    usd_eur_fx_rate=None,
    usd_eur_fx_provenance=None,
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
            risk_free_rate=float(risk_free_rate),
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
        enriched["risk_free_rate"] = dict(
            risk_free_rate_provenance
        )

        sizing_input = adapt_sizing_input_v3(
            enriched,
            risk_context,
            usd_eur_rate=usd_eur_fx_rate,
        )

        sizing_kwargs = sizing_input.to_dict()

        if enriched.get("strategy") == "covered_call":
            raise OptionsDataAdapterError(
                "covered_call: certified EUR risk model required"
            )

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
        enriched["sizing_currency"] = "EUR"
        enriched["contract_economics_source_currency"] = "USD"
        enriched["sizing_fx"] = dict(
            usd_eur_fx_provenance or {}
        )

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


def choose_strategy(signal, volatility_context=None):
    """
    Choose strategy using certified Options V3 volatility provenance.

    Mature provider-backed IV Rank may refine strategy selection.
    Before maturity, the runtime remains operational through defined-risk
    strategies instead of inventing IV Rank or rejecting valid direction.
    """
    direction = signal.get("direction", "neutral")
    signal_type = signal.get("signal_type", "")

    vol = (
        volatility_context
        if isinstance(volatility_context, dict)
        else {}
    )

    iv_rank = vol.get("iv_rank")
    iv_rank_status = vol.get(
        "iv_rank_status",
        "WARMING_UP",
    )

    mature_iv = (
        iv_rank_status == "AVAILABLE"
        and isinstance(iv_rank, (int, float))
    )

    if direction == "bearish":
        return (
            "bear_put_spread",
            "hedge",
            "unknown",
            "SELECTED",
            None,
        )

    if direction in ["bullish", "strong_bullish"]:
        if mature_iv and float(iv_rank) < 50:
            strategy = "long_call"
            reason = "selected_from_available_iv_rank"
        elif mature_iv:
            strategy = "bull_call_spread"
            reason = "selected_from_available_iv_rank"
        else:
            strategy = "bull_call_spread"
            reason = "defined_risk_fallback_iv_warming_up"

        return (
            strategy,
            "alpha",
            (
                "available"
                if mature_iv
                else "warming_up"
            ),
            "SELECTED",
            reason,
        )

    if direction == "neutral_to_bullish":
        if mature_iv and float(iv_rank) >= 50:
            strategy = "cash_secured_put"
            reason = "selected_from_available_iv_rank"
        elif mature_iv:
            strategy = "bull_put_spread"
            reason = "selected_from_available_iv_rank"
        else:
            strategy = "bull_put_spread"
            reason = "defined_risk_fallback_iv_warming_up"

        return (
            strategy,
            "entry_yield",
            (
                "available"
                if mature_iv
                else "warming_up"
            ),
            "SELECTED",
            reason,
        )

    if signal_type == "existing_equity_overlay":
        return (
            "covered_call",
            "yield",
            (
                "available"
                if mature_iv
                else "warming_up"
            ),
            "SELECTED",
            None,
        )

    return (
        "neutral_spread",
        "neutral",
        (
            "available"
            if mature_iv
            else "warming_up"
        ),
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

def build_candidate(signal, volatility_context=None):
    ticker = signal.get("ticker")

    vol = (
        volatility_context
        if isinstance(volatility_context, dict)
        else {}
    )

    (
        strategy,
        role,
        vol_regime,
        strategy_selection_status,
        strategy_selection_reason,
    ) = choose_strategy(
        signal,
        vol,
    )

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

        # Certified Options V3 volatility provenance.
        "iv_rank": vol.get("iv_rank"),
        "iv_rank_status": vol.get(
            "iv_rank_status",
            IV_RANK_STATUS_UNAVAILABLE,
        ),
        "iv_percentile": vol.get(
            "iv_percentile"
        ),
        "iv_percentile_status": vol.get(
            "iv_percentile_status",
            IV_PERCENTILE_STATUS_UNAVAILABLE,
        ),
        "iv_provenance_status": vol.get(
            "iv_provenance_status",
            IV_PROVENANCE_STATUS,
        ),
        "iv_observation_count": vol.get(
            "observation_count",
            0,
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
                f"{vol.get('iv_rank')}"
            ),
            (
                "iv_rank_status="
                f"{vol.get('iv_rank_status', IV_RANK_STATUS_UNAVAILABLE)}"
            ),
            (
                "iv_percentile="
                f"{vol.get('iv_percentile')}"
            ),
            (
                "iv_percentile_status="
                f"{vol.get('iv_percentile_status', IV_PERCENTILE_STATUS_UNAVAILABLE)}"
            ),
            (
                "iv_provenance_status="
                f"{vol.get('iv_provenance_status', IV_PROVENANCE_STATUS)}"
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

    return True, "approved"

def build_existing_position_valuations_v3(
    open_positions: list,
    *,
    usd_eur_rate: float,
    fx_provenance: dict,
    quote_fetcher=fetch_position_contract_quotes_v3,
) -> tuple[dict, dict]:
    if not isinstance(open_positions, list):
        raise RuntimeError(
            "options_v3_valuation_orchestration: "
            "open_positions must be a list"
        )

    valuations = {}
    failures = {}

    for position in open_positions:
        if not isinstance(position, dict):
            continue

        position_id = str(
            position.get("position_id") or ""
        ).strip()
        ticker = str(
            position.get("ticker") or ""
        ).strip().upper()
        expiration = str(
            position.get("expiration") or ""
        ).strip()

        legs = position.get("contract_legs")

        if (
            not position_id
            or not ticker
            or not expiration
            or not isinstance(legs, list)
            or not legs
        ):
            key = position_id or "<unknown>"
            failures[key] = (
                "INVALID_CANONICAL_POSITION"
            )
            continue

        contract_symbols = []

        invalid_leg = False

        for leg in legs:
            if not isinstance(leg, dict):
                invalid_leg = True
                break

            symbol = str(
                leg.get("contract_symbol") or ""
            ).strip()

            if not symbol:
                invalid_leg = True
                break

            contract_symbols.append(symbol)

        if invalid_leg or not contract_symbols:
            failures[position_id] = (
                "INVALID_CANONICAL_CONTRACT_LEGS"
            )
            continue

        try:
            quote_payload = quote_fetcher(
                ticker,
                expiration=expiration,
                contract_symbols=contract_symbols,
            )

            if not isinstance(quote_payload, dict):
                raise RuntimeError(
                    "held-contract quote payload must be dict"
                )

            quotes = quote_payload.get("contracts")
            metadata = quote_payload.get("metadata")

            if not isinstance(quotes, list) or not quotes:
                raise RuntimeError(
                    "held-contract quotes unavailable"
                )

            if not isinstance(metadata, dict):
                raise RuntimeError(
                    "held-contract quote metadata required"
                )

            valuation = value_open_position_v3(
                position,
                quotes,
                usd_eur_rate=usd_eur_rate,
                fx_provenance=fx_provenance,
            )

            valuation["market_data_provenance"] = {
                "provider": metadata.get("provider"),
                "provider_version": metadata.get(
                    "provider_version"
                ),
                "ticker": metadata.get("ticker"),
                "expiration": metadata.get("expiration"),
                "retrieval_timestamp": metadata.get(
                    "retrieval_timestamp"
                ),
                "requested_contract_count": metadata.get(
                    "requested_contract_count"
                ),
                "returned_contract_count": metadata.get(
                    "returned_contract_count"
                ),
                "lookup_policy": metadata.get(
                    "lookup_policy"
                ),
                "liquidity_gate_applied": metadata.get(
                    "liquidity_gate_applied"
                ),
                "market_quote_age_verified": False,
            }

            valuations[position_id] = valuation

        except (
            OptionChainProviderError,
            OptionsPositionValuationError,
            RuntimeError,
        ) as exc:
            failures[position_id] = (
                f"{type(exc).__name__}:{exc}"
            )

    return valuations, failures


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

    volatility_context_by_ticker = {}

    for ticker in sorted({
        str(signal.get("ticker") or "").strip().upper()
        for signal in all_signals
        if isinstance(signal, dict)
        and str(signal.get("ticker") or "").strip()
    }):
        try:
            volatility_context_by_ticker[
                ticker
            ] = observe_and_update_iv_history(
                ticker,
                history_path=(
                    OUT / "iv_history_v3.json"
                ),
                cache_dir=(
                    OPTIONS_V3_OPTION_CHAIN_CACHE_DIR
                ),
            )

        except (
            IVObservationError,
            OptionChainProviderError,
        ) as exc:
            volatility_context_by_ticker[
                ticker
            ] = {
                "iv_rank": None,
                "iv_percentile": None,
                "iv_rank_status": "UNAVAILABLE",
                "iv_percentile_status": "UNAVAILABLE",
                "iv_provenance_status": (
                    "PROVIDER_OBSERVATION_FAILED"
                ),
                "observation_count": 0,
                "observation_error": (
                    f"{type(exc).__name__}:{exc}"
                ),
            }

    candidates_raw = [
        build_candidate(
            signal,
            volatility_context_by_ticker.get(
                str(
                    signal.get("ticker") or ""
                ).strip().upper(),
                {},
            ),
        )
        for signal in all_signals
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

    # One certified nominal risk-free snapshot is shared by all
    # Black-Scholes calculations in this cycle.
    risk_free_network_authorized = (
        os.getenv(
            "NSC_OPTIONS_V3_FRED_NETWORK_AUTHORIZED",
            "",
        ).strip().lower()
        in {"1", "true", "yes"}
    )

    if not risk_free_network_authorized:
        raise RuntimeError(
            "options_v3_risk_free_rate_network_not_authorized"
        )

    try:
        cycle_risk_free_rate_raw = (
            fetch_certified_risk_free_rate_network_v3(
                network_authorized=True,
            )
        )
    except Exception as exc:
        raise RuntimeError(
            "options_v3_risk_free_rate_unavailable:"
            f"{type(exc).__name__}:{exc}"
        ) from exc

    cycle_risk_free_rate = float(
        cycle_risk_free_rate_raw["risk_free_rate"]
    )

    # JSON-safe certified provenance for artifacts and candidate audit.
    cycle_risk_free_rate_provenance = {
        "provider": str(
            cycle_risk_free_rate_raw["provider"]
        ),
        "series_id": str(
            cycle_risk_free_rate_raw["series_id"]
        ),
        "observation_date": str(
            cycle_risk_free_rate_raw["observation_date"]
        ),
        "retrieved_at": str(
            cycle_risk_free_rate_raw["retrieved_at"]
        ),
        "raw_rate_percent": float(
            cycle_risk_free_rate_raw["raw_rate_percent"]
        ),
        "risk_free_rate": cycle_risk_free_rate,
        "source_unit": str(
            cycle_risk_free_rate_raw["source_unit"]
        ),
        "normalized_unit": str(
            cycle_risk_free_rate_raw["normalized_unit"]
        ),
        "age_days": int(
            cycle_risk_free_rate_raw["age_days"]
        ),
        "max_age_days": int(
            cycle_risk_free_rate_raw["max_age_days"]
        ),
        "freshness_verified": bool(
            cycle_risk_free_rate_raw[
                "freshness_verified"
            ]
        ),
    }

    # One certified USD/EUR snapshot is shared by existing
    # position valuation and new-position sizing in this cycle.
    try:
        cycle_fx_rate = FXService().get_rate(
            "USD",
            "EUR",
        )
    except FXServiceError as exc:
        raise RuntimeError(
            f"options_v3_cycle_fx_unavailable:{exc}"
        ) from exc

    cycle_usd_eur_rate = float(
        cycle_fx_rate.rate
    )
    cycle_fx_provenance = cycle_fx_rate.to_dict()

    # Read the canonical inventory before lifecycle reconciliation
    # so exact held-contract marks can be injected into that pass.
    existing_inventory = load(
        OUT / "options_v3_positions.json",
        [],
    )
    closed_inventory_before = load(
        OUT / "options_v3_positions_closed.json",
        [],
    )

    if not isinstance(existing_inventory, list):
        raise RuntimeError(
            "options_v3_positions must be a list"
        )

    if not isinstance(closed_inventory_before, list):
        raise RuntimeError(
            "options_v3_positions_closed must be a list"
        )

    existing_valuations, valuation_failures = (
        build_existing_position_valuations_v3(
            existing_inventory,
            usd_eur_rate=cycle_usd_eur_rate,
            fx_provenance=cycle_fx_provenance,
        )
    )

    # Existing inventory is lifecycle-evaluated before
    # any new sizing/allocation. Current candidate selection
    # must never define whether an already-open position exists.
    #
    # A position without a certified current valuation remains
    # OPEN with PnL unavailable; another position's market-data
    # failure must not fabricate a mark or close the inventory.
    pre_allocation_open_positions, _ = (
        reconcile_existing_positions_v3(
            valuations_by_position_id=(
                existing_valuations
            ),
        )
    )

    existing_used_risk_eur = calculate_open_risk_v3(
        pre_allocation_open_positions
    )

    options_available_risk_eur = max(
        0.0,
        options_max_total_risk_eur
        - existing_used_risk_eur,
    )

    # The exact same certified FX snapshot is reused for sizing.
    sizing_usd_eur_rate = cycle_usd_eur_rate
    sizing_fx_provenance = dict(
        cycle_fx_provenance
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
                            options_available_risk_eur,
                        "internal_max_trade_risk_eur":
                            options_max_trade_risk_eur,
                    },
                    risk_free_rate=(
                        cycle_risk_free_rate
                    ),
                    risk_free_rate_provenance=(
                        cycle_risk_free_rate_provenance
                    ),
                    usd_eur_fx_rate=(
                        sizing_usd_eur_rate
                    ),
                    usd_eur_fx_provenance=(
                        sizing_fx_provenance
                    ),
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
        existing_used_risk_eur=existing_used_risk_eur,
        existing_open_positions_count=len(
            pre_allocation_open_positions
        ),
        max_open_positions=5,
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

    position_valuation_failure_count = len(
        valuation_failures
    )

    position_valuation_status = (
        "DEGRADED"
        if position_valuation_failure_count
        else "COMPLETE"
    )

    pipeline_status = (
        "degraded"
        if (
            infrastructure_failure_reasons
            or position_valuation_failure_count
        )
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
            "position_valuation_status": (
                position_valuation_status
            ),
            "position_valuation_failure_count": (
                position_valuation_failure_count
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
        "risk_free_rate": dict(
            cycle_risk_free_rate_provenance
        ),
        "position_valuation": {
            "status": position_valuation_status,
            "valued_position_count": len(
                existing_valuations
            ),
            "failure_count": (
                position_valuation_failure_count
            ),
            "failures": dict(
                valuation_failures
            ),
            "market_quote_age_verified": False,
        },
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

    open_positions, closed_positions = (
        open_selected_positions_v3(
            portfolio.get("selected", [])
        )
    )

    options_v3_performance = (
        build_options_performance_v3(
            open_positions=open_positions,
            closed_positions=closed_positions,
            as_of=datetime.now(timezone.utc),
        )
    )
    save(
        "options_v3_performance.json",
        options_v3_performance,
    )

    # Reconcile risk to the actual surviving OPEN inventory.
    # This is the canonical post-lifecycle risk state.
    final_open_risk_eur = calculate_open_risk_v3(
        open_positions
    )

    portfolio["planned_used_risk_eur"] = (
        portfolio.get("used_risk_eur", 0)
    )
    portfolio["final_open_risk_eur"] = round(
        final_open_risk_eur,
        2,
    )
    portfolio["used_risk_eur"] = round(
        final_open_risk_eur,
        2,
    )
    portfolio["used_risk_pct"] = round(
        final_open_risk_eur / options_capital_eur,
        4,
    )
    portfolio["available_risk_eur_after_new"] = round(
        max(
            0.0,
            options_max_total_risk_eur
            - final_open_risk_eur,
        ),
        2,
    )
    portfolio["risk_reconciliation_status"] = (
        "RECONCILED_TO_OPEN_INVENTORY"
    )

    save("options_v3_portfolio.json", portfolio)


    save("options_v3_candidates_validated.json", candidates_validated)
    save("options_v3_decisions.json", decisions)
    # ===== DASHBOARD POSITIONS POST-WRITE FIX =====
    open_positions_file = load(OUT / "options_v3_positions.json", [])
    closed_positions_file = load(OUT / "options_v3_positions_closed.json", [])

    dashboard["positions"] = {
        "open": len(open_positions_file),
        "closed": len(closed_positions_file),
    }

    dashboard["portfolio"].update(
        {
            "existing_used_risk_eur":
                portfolio.get(
                    "existing_used_risk_eur",
                    0,
                ),
            "new_allocated_risk_eur":
                portfolio.get(
                    "new_allocated_risk_eur",
                    0,
                ),
            "planned_used_risk_eur":
                portfolio.get(
                    "planned_used_risk_eur",
                    0,
                ),
            "used_risk_eur":
                portfolio.get(
                    "used_risk_eur",
                    0,
                ),
            "used_risk_pct":
                portfolio.get(
                    "used_risk_pct",
                    0,
                ),
            "available_risk_eur_after_new":
                portfolio.get(
                    "available_risk_eur_after_new",
                    0,
                ),
            "risk_reconciliation_status":
                portfolio.get(
                    "risk_reconciliation_status"
                ),
        }
    )

    save("options_v3_dashboard.json", dashboard)

    status_payload = {
        "status": "ok",
        "health": {
            "dashboard_artifact": True,
            "positions_artifact": True,
            "portfolio_artifact": True,
            "position_valuation": (
                position_valuation_status
            ),
            "position_valuation_failure_count": (
                position_valuation_failure_count
            ),
            "position_valuation_failures": dict(
                valuation_failures
            ),
        },
        "risk_free_rate": dict(
            cycle_risk_free_rate_provenance
        ),
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

    # Append one compact longitudinal observation only after
    # canonical position lifecycle and final risk reconciliation
    # have completed for this cycle.
    ledger_observed_at = now()

    cycle_ledger_entry = build_cycle_ledger_entry_v3(
        observed_at=ledger_observed_at,
        pipeline_status=pipeline_status,
        opportunity_status=opportunity_status,
        infrastructure_failure_count=len(
            infrastructure_failure_reasons
        ),
        signals_total=len(all_signals),
        candidates_raw=len(candidates_raw),
        candidates_validated=len(candidates_validated),
        decisions_total=len(decisions),
        approved_count=len(
            [
                d
                for d in decisions
                if d["status"] == "APPROVED"
            ]
        ),
        rejected_count=len(
            [
                d
                for d in decisions
                if d["status"] == "REJECTED"
            ]
        ),
        valuation_status=position_valuation_status,
        valued_position_count=len(
            existing_valuations
        ),
        valuation_failure_count=(
            position_valuation_failure_count
        ),
        open_positions_before=existing_inventory,
        closed_positions_before=closed_inventory_before,
        open_positions_after=open_positions_file,
        closed_positions_after=closed_positions_file,
        existing_used_risk_eur=portfolio.get(
            "existing_used_risk_eur",
            0,
        ),
        new_allocated_risk_eur=portfolio.get(
            "new_allocated_risk_eur",
            0,
        ),
        final_open_risk_eur=portfolio.get(
            "final_open_risk_eur",
            portfolio.get("used_risk_eur", 0),
        ),
        used_risk_pct=portfolio.get(
            "used_risk_pct",
            0,
        ),
        available_risk_eur_after_new=portfolio.get(
            "available_risk_eur_after_new",
            0,
        ),
        risk_free_rate_provenance=(
            cycle_risk_free_rate_provenance
        ),
    )

    append_cycle_ledger_entry_v3(
        OUT / "options_v3_cycle_history.jsonl",
        cycle_ledger_entry,
    )

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
