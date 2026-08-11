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
    "external_signals": SRC / "options/data/external_signals.json",
    "external_watchlists": SRC / "options/data/external_watchlists.json",
    "external_equity_positions": SRC / "options/data/external_equity_positions.json",
    "volatility_context": SRC / "options_v2/data/volatility_context_v2.json",
    "v2_dashboard": SRC / "options_v2/data/options_v2_dashboard.json",
    "v2_decisions": SRC / "options_v2/data/options_v2_decisions.json",
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

def vol_for(ticker, volatility_context):
    tickers = volatility_context.get("tickers", {})
    if isinstance(tickers, dict):
        return tickers.get(ticker, {})
    if isinstance(tickers, list):
        for item in tickers:
            if item.get("ticker") == ticker:
                return item
    return {}

def choose_strategy(signal, vol):
    direction = signal.get("direction", "neutral")
    signal_type = signal.get("signal_type", "")
    iv_rank = float(vol.get("iv_rank") or 0)
    vol_regime = vol.get("vol_regime") or ("high" if iv_rank >= 60 else "mid")

    if direction == "bearish":
        strategy = "bear_put_spread"
        role = "hedge"
    elif direction in ["bullish", "strong_bullish"]:
        strategy = "bull_call_spread" if iv_rank >= 50 else "long_call"
        role = "alpha"
    elif direction == "neutral_to_bullish":
        strategy = "cash_secured_put" if iv_rank >= 50 else "bull_put_spread"
        role = "entry_yield"
    elif signal_type == "existing_equity_overlay":
        strategy = "covered_call"
        role = "yield"
    else:
        strategy = "neutral_spread"
        role = "neutral"

    return strategy, role, vol_regime

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

def build_candidate(signal, volatility_context):
    ticker = signal.get("ticker")
    vol = vol_for(ticker, volatility_context)
    strategy, role, vol_regime = choose_strategy(signal, vol)

    confidence = float(signal.get("confidence") or 0.5)
    spot = float(signal.get("spot") or vol.get("spot") or vol.get("underlying_spot") or 0)
    risk = estimate_risk(strategy, spot)

    score = round(
        confidence * 60
        + min(float(vol.get("iv_rank") or 0), 100) * 0.25
        + (10 if role in ["alpha", "hedge"] else 5),
        2
    )

    return {
        "ts": now(),
        "ticker": ticker,
        "strategy": strategy,
        "direction": signal.get("direction", "neutral"),
        "role": role,
        "score": score,
        "confidence": confidence,
        "estimated_risk_eur": risk,
        "vol_regime": vol_regime,
        "iv_rank": vol.get("iv_rank"),
        "source_signal": signal,
        "underlying_equity_quantity": signal.get(
            "underlying_equity_quantity"
        ),
        "explain": [
            f"direction={signal.get('direction')}",
            f"strategy={strategy}",
            f"role={role}",
            f"vol_regime={vol_regime}",
        ],
    }

def validate(candidate):
    if not candidate.get("ticker"):
        return False, "missing_ticker"

    if candidate["score"] < 55:
        return False, "score_below_threshold"

    if candidate["estimated_risk_eur"] > 2000:
        return False, "risk_above_limit"

    return True, "approved"

def main():
    open_positions = []
    closed_positions = []
    print("===== OPTIONS V3 AUTONOMOUS SHADOW RUN =====")

    external_signals = load(PATHS["external_signals"], [])
    external_positions = load(PATHS["external_equity_positions"], [])
    volatility_context = load(PATHS["volatility_context"], {})
    v2_dashboard = load(PATHS["v2_dashboard"], {})
    v2_decisions = load(PATHS["v2_decisions"], [])

    overlay_signals = []
    for p in external_positions:
        overlay_signals.append({
            "ticker": p.get("ticker"),
            "signal_type": "existing_equity_overlay",
            "direction": "neutral",
            "confidence": 0.65,
            "setup": "covered_call_candidate",
            "spot": p.get("current_price"),
            "underlying_equity_quantity": p.get("quantity"),
        })

    all_signals = external_signals + overlay_signals

    candidates_raw = [build_candidate(s, volatility_context) for s in all_signals]

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

            if c.get("capability_enrichment_status") != "complete":
                ok = False
                reason = c.get(
                    "capability_rejection_reason",
                    "options_v3_capability_enrichment_failed",
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
        "comparison_reference": {
            "v2_realized_pnl_eur": v2_dashboard.get("kpis", {}).get("realized_pnl_eur"),
            "v2_win_rate_pct": v2_dashboard.get("kpis", {}).get("win_rate_pct"),
            "v2_decisions_count": len(v2_decisions) if isinstance(v2_decisions, list) else 0,
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
