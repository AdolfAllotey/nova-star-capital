from datetime import datetime, timezone
from typing import List, Dict, Any

from options_v2.builders.covered_call_builder import build_covered_call
from options_v2.builders.cash_secured_put_builder import build_cash_secured_put
from options_v2.builders.vertical_spread_builder import build_vertical_spread


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_position_for_ticker(positions: List[Dict[str, Any]], ticker: str):
    for pos in positions:
        if pos.get("ticker") == ticker and pos.get("type") == "equity":
            return pos
    return None


def _is_in_watchlist(watchlists: Dict[str, List[str]], ticker: str, list_name: str) -> bool:
    return ticker in set(watchlists.get(list_name, []))


def _blocked_candidate(
    ticker: str,
    signal: Dict[str, Any],
    vol_ctx: Dict[str, Any],
    reason: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "ts": utc_now_iso(),
        "ticker": ticker,
        "approved_signal": False,
        "blocked_reason": reason,
        "blocked_details": details or {},
        "vol_context": vol_ctx,
        "source_signal": signal,
    }


def generate_options_candidates(
    signals: List[Dict[str, Any]],
    positions: List[Dict[str, Any]],
    watchlists: Dict[str, List[str]],
    volatility_context: Dict[str, Any],
    governance: Dict[str, Any],
) -> List[Dict[str, Any]]:
    allowed_strategies = set(governance.get("allowed_strategies", []))
    vol_map = volatility_context.get("tickers", {})
    candidates: List[Dict[str, Any]] = []

    min_confidence = governance.get("min_confidence_by_strategy", {})
    covered_call_min_conf = float(min_confidence.get("covered_call", 0.70))
    cash_secured_put_min_conf = float(min_confidence.get("cash_secured_put", 0.65))
    vertical_spread_min_conf = float(min_confidence.get("vertical_spread", 0.70))

    covered_call_requires_sell_vol = bool(governance.get("covered_call_requires_sell_vol", True))
    cash_secured_put_requires_sell_vol = bool(governance.get("cash_secured_put_requires_sell_vol", True))
    vertical_spread_allow_buy_or_neutral_vol = bool(governance.get("vertical_spread_allow_buy_or_neutral_vol", True))

    for signal in signals:
        ticker = signal.get("ticker")
        if not ticker:
            continue

        vol_ctx = vol_map.get(ticker, {})
        strategy_bias = vol_ctx.get("strategy_bias", "neutral")
        vol_regime = vol_ctx.get("vol_regime", "unknown")
        event_risk = vol_ctx.get("event_risk", False)

        if governance.get("block_near_events", True) and event_risk:
            candidates.append(_blocked_candidate(
                ticker=ticker,
                signal=signal,
                vol_ctx=vol_ctx,
                reason="event_risk",
                details={"days_to_event": vol_ctx.get("days_to_event")}
            ))
            continue

        position = _find_position_for_ticker(positions, ticker)
        confidence = float(signal.get("confidence", 0.0))
        signal_type = signal.get("signal_type")
        direction = signal.get("direction")

        # COVERED CALL
        if signal_type in {"portfolio_overlay", "income_overlay"}:
            if "covered_call" not in allowed_strategies:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "strategy_not_allowed", {"strategy": "covered_call"}
                ))
                continue

            if position is None:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "missing_underlying_position", {"strategy": "covered_call"}
                ))
                continue

            if int(position.get("quantity", 0)) < 100:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "insufficient_underlying_quantity", {
                        "strategy": "covered_call",
                        "required_quantity": 100,
                        "current_quantity": int(position.get("quantity", 0))
                    }
                ))
                continue

            if confidence < covered_call_min_conf:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "confidence_below_threshold", {
                        "strategy": "covered_call",
                        "confidence": confidence,
                        "min_required": covered_call_min_conf
                    }
                ))
                continue

            if covered_call_requires_sell_vol and strategy_bias != "sell_vol":
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "vol_bias_incompatible", {
                        "strategy": "covered_call",
                        "required_bias": "sell_vol",
                        "current_bias": strategy_bias,
                        "vol_regime": vol_regime
                    }
                ))
                continue

            structure = build_covered_call(position, vol_ctx)
            candidates.append({
                "ts": utc_now_iso(),
                "ticker": ticker,
                "approved_signal": True,
                "strategy": "covered_call",
                "confidence": confidence,
                "selection_reason": "income_overlay_on_existing_position_with_sell_vol_context",
                "selection_context": {
                    "signal_type": signal_type,
                    "direction": direction,
                    "strategy_bias": strategy_bias,
                    "vol_regime": vol_regime
                },
                "source_signal": signal,
                "structure": structure,
            })
            continue

        # CASH SECURED PUT
        if signal_type in {"watchlist_entry", "defensive_entry"}:
            if "cash_secured_put" not in allowed_strategies:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "strategy_not_allowed", {"strategy": "cash_secured_put"}
                ))
                continue

            if not (
                _is_in_watchlist(watchlists, ticker, "defensive")
                or _is_in_watchlist(watchlists, ticker, "offensive")
            ):
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "ticker_not_in_authorized_watchlist", {
                        "strategy": "cash_secured_put"
                    }
                ))
                continue

            if confidence < cash_secured_put_min_conf:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "confidence_below_threshold", {
                        "strategy": "cash_secured_put",
                        "confidence": confidence,
                        "min_required": cash_secured_put_min_conf
                    }
                ))
                continue

            if cash_secured_put_requires_sell_vol and strategy_bias != "sell_vol":
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "vol_bias_incompatible", {
                        "strategy": "cash_secured_put",
                        "required_bias": "sell_vol",
                        "current_bias": strategy_bias,
                        "vol_regime": vol_regime
                    }
                ))
                continue

            structure = build_cash_secured_put(signal, vol_ctx)
            candidates.append({
                "ts": utc_now_iso(),
                "ticker": ticker,
                "approved_signal": True,
                "strategy": "cash_secured_put",
                "confidence": confidence,
                "selection_reason": "paid_entry_on_watchlist_name_with_sell_vol_context",
                "selection_context": {
                    "signal_type": signal_type,
                    "direction": direction,
                    "strategy_bias": strategy_bias,
                    "vol_regime": vol_regime
                },
                "source_signal": signal,
                "structure": structure,
            })
            continue

        # VERTICAL SPREAD
        if signal_type in {"offensive", "directional_trade"}:
            if "vertical_spread" not in allowed_strategies:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "strategy_not_allowed", {"strategy": "vertical_spread"}
                ))
                continue

            if not _is_in_watchlist(watchlists, ticker, "offensive"):
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "ticker_not_in_offensive_watchlist", {
                        "strategy": "vertical_spread"
                    }
                ))
                continue

            if direction not in {"bullish", "neutral_to_bullish"}:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "direction_incompatible", {
                        "strategy": "vertical_spread",
                        "direction": direction
                    }
                ))
                continue

            if confidence < vertical_spread_min_conf:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "confidence_below_threshold", {
                        "strategy": "vertical_spread",
                        "confidence": confidence,
                        "min_required": vertical_spread_min_conf
                    }
                ))
                continue

            if not vertical_spread_allow_buy_or_neutral_vol and strategy_bias not in {"buy_vol", "neutral"}:
                candidates.append(_blocked_candidate(
                    ticker, signal, vol_ctx, "vol_bias_incompatible", {
                        "strategy": "vertical_spread",
                        "allowed_biases": ["buy_vol", "neutral"],
                        "current_bias": strategy_bias,
                        "vol_regime": vol_regime
                    }
                ))
                continue

            structure = build_vertical_spread(signal, vol_ctx)
            candidates.append({
                "ts": utc_now_iso(),
                "ticker": ticker,
                "approved_signal": True,
                "strategy": "vertical_spread",
                "confidence": confidence,
                "selection_reason": "defined_risk_directional_trade_from_offensive_signal",
                "selection_context": {
                    "signal_type": signal_type,
                    "direction": direction,
                    "strategy_bias": strategy_bias,
                    "vol_regime": vol_regime
                },
                "source_signal": signal,
                "structure": structure,
            })
            continue

        candidates.append(_blocked_candidate(
            ticker=ticker,
            signal=signal,
            vol_ctx=vol_ctx,
            reason="no_matching_strategy_rule",
            details={
                "signal_type": signal_type,
                "direction": direction
            }
        ))

    return candidates
