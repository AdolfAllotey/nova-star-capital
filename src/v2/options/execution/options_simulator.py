from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple


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


def should_mark_position(position: Dict[str, Any], min_hours_between_marks: int) -> bool:
    last_mark_ts = position.get("last_mark_ts")
    if not last_mark_ts:
        return True

    last_dt = parse_iso(last_mark_ts)
    if last_dt is None:
        return True

    delta = utc_now() - last_dt
    return delta.total_seconds() >= (min_hours_between_marks * 3600)


def _build_position_from_candidate(
    candidate: Dict[str, Any],
    default_take_profit_pct: float,
    default_stop_loss_pct: float,
) -> Dict[str, Any]:
    structure = candidate.get("structure", {})
    strategy = candidate.get("strategy")
    estimated_risk_eur = float(candidate.get("risk_validation", {}).get("estimated_risk_eur", 0.0))

    if strategy == "covered_call":
        entry_value = float(structure.get("estimated_premium_per_share", 0.0)) * 100 * int(structure.get("contract_count", 0))
    elif strategy == "cash_secured_put":
        entry_value = float(structure.get("estimated_premium_per_share", 0.0)) * 100 * int(structure.get("contract_count", 1))
    else:
        entry_value = -float(structure.get("estimated_debit_per_share", 0.0)) * 100 * int(structure.get("contract_count", 1))

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
        "take_profit_pct": float(default_take_profit_pct),
        "stop_loss_pct": float(default_stop_loss_pct),
    }


def _daily_mark_to_model(position: Dict[str, Any]) -> Dict[str, Any]:
    strategy = position.get("strategy")
    entry_value = float(position.get("entry_value_eur", 0.0))
    current_value = float(position.get("current_value_eur", 0.0))
    days_to_expiry = int(position.get("days_to_expiry", 0))
    days_in_trade = int(position.get("days_in_trade", 0))

    if strategy in {"covered_call", "cash_secured_put"}:
        decay = max(abs(entry_value) * 0.08, 1.0)
        new_value = current_value - decay
        pnl_eur = entry_value - new_value if entry_value >= 0 else abs(entry_value) - abs(new_value)
    else:
        improvement = max(abs(entry_value) * 0.05, 1.0)
        new_value = current_value + improvement
        pnl_eur = new_value - entry_value

    days_in_trade += 1
    days_to_expiry = max(days_to_expiry - 1, 0)
    pnl_pct = (pnl_eur / abs(entry_value)) * 100 if entry_value != 0 else 0.0

    position["current_value_eur"] = round(new_value, 2)
    position["days_in_trade"] = days_in_trade
    position["days_to_expiry"] = days_to_expiry
    position["pnl_eur"] = round(pnl_eur, 2)
    position["pnl_pct"] = round(pnl_pct, 2)
    position["last_mark_ts"] = utc_now_iso()
    return position


def _should_close(position: Dict[str, Any]) -> Tuple[bool, str]:
    pnl_pct = float(position.get("pnl_pct", 0.0))
    days_to_expiry = int(position.get("days_to_expiry", 0))

    if pnl_pct >= float(position.get("take_profit_pct", 75.0)):
        return True, "take_profit"
    if pnl_pct <= float(position.get("stop_loss_pct", -50.0)):
        return True, "stop_loss"
    if days_to_expiry <= 5:
        return True, "close_before_expiry"

    return False, ""


def simulate_options_candidates(
    validated_candidates: List[Dict[str, Any]],
    existing_positions: List[Dict[str, Any]],
    existing_trades: List[Dict[str, Any]],
    mode: str = "SIMULATION",
    simulation_config: Dict[str, Any] | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    simulation_config = simulation_config or {}
    min_hours_between_marks = int(simulation_config.get("min_hours_between_marks", 24))
    default_take_profit_pct = float(simulation_config.get("default_take_profit_pct", 75.0))
    default_stop_loss_pct = float(simulation_config.get("default_stop_loss_pct", -50.0))

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

        key = f"{candidate.get('ticker')}|{candidate.get('strategy')}|OPEN"
        if key in already_open_keys:
            continue

        new_position = _build_position_from_candidate(
            candidate=candidate,
            default_take_profit_pct=default_take_profit_pct,
            default_stop_loss_pct=default_stop_loss_pct,
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

    for position in positions:
        if position.get("status") != "OPEN":
            continue

        if not should_mark_position(position, min_hours_between_marks):
            continue

        _daily_mark_to_model(position)
        should_close, close_reason = _should_close(position)

        if should_close:
            position["status"] = "CLOSED"
            position["ts_close"] = utc_now_iso()
            position["close_reason"] = close_reason

            trades.append({
                "ts": utc_now_iso(),
                "action": "CLOSE",
                "ticker": position.get("ticker"),
                "strategy": position.get("strategy"),
                "pnl_eur": position.get("pnl_eur"),
                "pnl_pct": position.get("pnl_pct"),
                "reason": close_reason,
                "mode": mode,
            })

    return positions, trades
