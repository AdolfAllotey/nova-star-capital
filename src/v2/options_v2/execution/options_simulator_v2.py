from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from options_v2.execution.pnl_engine import repricing_position_v2
from options_v2.execution.position_lifecycle import should_close_position_v2, close_position_v2


def utc_now():
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_iso(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def should_mark_position(position: Dict[str, Any], min_hours_between_marks: int) -> bool:
    last_mark_ts = position.get("last_mark_ts")
    if not last_mark_ts:
        return True

    last_dt = parse_iso(last_mark_ts)
    if last_dt is None:
        return True

    delta = utc_now() - last_dt
    return delta.total_seconds() >= (min_hours_between_marks * 3600)


def recently_closed_same_trade(
    trades: List[Dict[str, Any]],
    ticker: str,
    strategy: str,
    cooldown_hours_after_close: int,
) -> bool:
    if cooldown_hours_after_close <= 0:
        return False

    now = utc_now()

    for trade in reversed(trades):
        if trade.get("action") != "CLOSE":
            continue
        if trade.get("ticker") != ticker:
            continue
        if trade.get("strategy") != strategy:
            continue

        ts = parse_iso(trade.get("ts"))
        if ts is None:
            continue

        delta = now - ts
        if delta.total_seconds() < cooldown_hours_after_close * 3600:
            return True

        return False

    return False


def _build_position_from_candidate(
    candidate: Dict[str, Any],
    simulation_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    simulation_config = simulation_config or {}

    structure = candidate.get("structure", {})
    strategy = candidate.get("strategy")
    estimated_risk_eur = safe_float(
        candidate.get("risk_validation", {}).get("estimated_risk_eur", 0.0),
        0.0,
    )

    if strategy == "covered_call":
        entry_value = safe_float(structure.get("estimated_premium_per_share", 0.0), 0.0) * 100 * int(structure.get("contract_count", 0))
    elif strategy == "cash_secured_put":
        entry_value = safe_float(structure.get("estimated_premium_per_share", 0.0), 0.0) * 100 * int(structure.get("contract_count", 1))
    else:
        entry_value = -safe_float(structure.get("estimated_debit_per_share", 0.0), 0.0) * 100 * int(structure.get("contract_count", 1))

    now_iso = utc_now_iso()

    return {
        "ts_open": now_iso,
        "last_mark_ts": None,
        "status": "OPEN",
        "ticker": candidate.get("ticker"),
        "strategy": strategy,
        "structure": structure,
        "entry_value_eur": round(entry_value, 2),
        "current_value_eur": round(entry_value, 2),
        "estimated_risk_eur": round(estimated_risk_eur, 2),
        "days_in_trade": 0,
        "days_to_expiry": int(structure.get("expiry_days", 0)),
        "pnl_eur": 0.0,
        "pnl_pct": 0.0,
        "take_profit_pct": safe_float(
            simulation_config.get("default_take_profit_pct", 50.0),
            50.0,
        ),
        "stop_loss_pct": safe_float(
            simulation_config.get("default_stop_loss_pct", -50.0),
            -50.0,
        ),
        "pricing_model": "v2_simplified_repricing",
    }


def simulate_options_candidates_v2(
    validated_candidates: List[Dict[str, Any]],
    existing_positions: List[Dict[str, Any]],
    existing_trades: List[Dict[str, Any]],
    mode: str = "SIMULATION",
    simulation_config: Dict[str, Any] | None = None,
    market_context: Dict[str, Any] | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    simulation_config = simulation_config or {}
    market_context = market_context or {}

    min_hours_between_marks = int(simulation_config.get("min_hours_between_marks", 24))
    cooldown_hours_after_close = int(simulation_config.get("cooldown_hours_after_close", 0))

    positions = existing_positions[:] if isinstance(existing_positions, list) else []
    trades = existing_trades[:] if isinstance(existing_trades, list) else []

    already_open_keys = {
        f"{p.get('ticker')}|{p.get('strategy')}|{p.get('status')}"
        for p in positions
        if p.get("status") == "OPEN"
    }

    for candidate in validated_candidates:
        rv = candidate.get("risk_validation", {})
        if not (candidate.get("approved_signal") and rv.get("approved")):
            continue

        ticker = candidate.get("ticker")
        strategy = candidate.get("strategy")
        key = f"{ticker}|{strategy}|OPEN"

        if key in already_open_keys:
            continue

        if recently_closed_same_trade(
            trades=trades,
            ticker=ticker,
            strategy=strategy,
            cooldown_hours_after_close=cooldown_hours_after_close,
        ):
            continue

        new_position = _build_position_from_candidate(
            candidate=candidate,
            simulation_config=simulation_config,
        )
        positions.append(new_position)
        already_open_keys.add(key)

        trades.append({
            "ts": utc_now_iso(),
            "action": "OPEN",
            "ticker": new_position.get("ticker"),
            "strategy": new_position.get("strategy"),
            "entry_value_eur": new_position.get("entry_value_eur"),
            "estimated_risk_eur": new_position.get("estimated_risk_eur"),
            "mode": mode,
        })

    lifecycle_config = {
        "default_take_profit_pct": safe_float(simulation_config.get("default_take_profit_pct", 50.0), 50.0),
        "default_stop_loss_pct": safe_float(simulation_config.get("default_stop_loss_pct", -50.0), -50.0),
        "force_close_days_to_expiry": int(simulation_config.get("force_close_days_to_expiry", 5)),
    }

    for position in positions:
        if position.get("status") != "OPEN":
            continue

        if not should_mark_position(position, min_hours_between_marks):
            continue

        repricing_position_v2(
            position=position,
            market_context=market_context,
            simulation_config=simulation_config,
        )

        should_close, close_reason = should_close_position_v2(
            position=position,
            lifecycle_config=lifecycle_config,
        )

        position["last_mark_ts"] = utc_now_iso()

        if should_close:
            trade_event = close_position_v2(
                position=position,
                reason=close_reason,
                mode=mode,
            )
            trades.append(trade_event)

    return positions, trades
