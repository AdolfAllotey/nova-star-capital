from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def compute_mock_underlying_return(
    position: Dict[str, Any],
    market_context: Dict[str, Any] | None = None,
) -> float:
    market_context = market_context or {}

    ticker = str(position.get("ticker", ""))
    strategy = str(position.get("strategy", ""))

    base_map = {
        "NVDA": 0.012,
        "MSFT": 0.006,
        "AAPL": 0.005,
        "KO": 0.002,
        "JNJ": 0.0015,
    }

    base_ret = base_map.get(ticker, 0.003)

    regime = str(market_context.get("global_regime", "neutral"))
    if regime == "risk_on":
        base_ret += 0.010
    elif regime == "risk_off":
        base_ret -= 0.015

    macro_bias = str(market_context.get("macro_bias", "balanced"))
    if macro_bias == "bullish":
        base_ret += 0.004
    elif macro_bias == "bearish":
        base_ret -= 0.004

    if strategy == "vertical_spread":
        base_ret += 0.001
    elif strategy in {"covered_call", "cash_secured_put"}:
        base_ret -= 0.0005

    return clamp(base_ret, -0.08, 0.08)


def compute_theta_decay_factor(
    position: Dict[str, Any],
    simulation_config: Dict[str, Any] | None = None,
) -> float:
    simulation_config = simulation_config or {}

    days_to_expiry = int(position.get("days_to_expiry", 0))
    base_theta = safe_float(simulation_config.get("base_theta_daily", 0.01), 0.01)

    if days_to_expiry > 30:
        factor = base_theta
    elif days_to_expiry > 15:
        factor = base_theta * 1.5
    elif days_to_expiry > 7:
        factor = base_theta * 2.0
    else:
        factor = base_theta * 3.0

    return clamp(factor, 0.0, 0.08)


def compute_vol_impact_factor(
    position: Dict[str, Any],
    market_context: Dict[str, Any] | None = None,
    simulation_config: Dict[str, Any] | None = None,
) -> float:
    simulation_config = simulation_config or {}
    market_context = market_context or {}

    vol_ctx = position.get("structure", {}).get("vol_context", {})
    iv_rank = safe_float(vol_ctx.get("iv_rank", 50.0), 50.0)

    centered = (iv_rank - 50.0) / 100.0
    weight = safe_float(simulation_config.get("vol_impact_weight", 0.15), 0.15)

    vol_regime = str(market_context.get("vol_regime", "normal"))
    regime_boost = 1.0
    if vol_regime == "high":
        regime_boost = 1.6
    elif vol_regime == "low":
        regime_boost = 0.7

    return clamp(centered * weight * regime_boost, -0.15, 0.15)


def repricing_position_v2(
    position: Dict[str, Any],
    market_context: Dict[str, Any] | None = None,
    simulation_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    market_context = market_context or {}
    simulation_config = simulation_config or {}

    strategy = str(position.get("strategy", ""))
    entry_value = safe_float(position.get("entry_value_eur", 0.0), 0.0)
    current_value = safe_float(position.get("current_value_eur", 0.0), entry_value)
    estimated_risk_eur = safe_float(position.get("estimated_risk_eur", 0.0), 0.0)
    days_in_trade = int(position.get("days_in_trade", 0))
    days_to_expiry = int(position.get("days_to_expiry", 0))

    underlying_ret = compute_mock_underlying_return(position=position, market_context=market_context)
    theta_factor = compute_theta_decay_factor(position=position, simulation_config=simulation_config)
    vol_factor = compute_vol_impact_factor(
        position=position,
        market_context=market_context,
        simulation_config=simulation_config,
    )

    directional_weight_vertical = safe_float(simulation_config.get("directional_weight_vertical", 0.45), 0.45)
    directional_weight_short_premium = safe_float(simulation_config.get("directional_weight_short_premium", 0.15), 0.15)

    current_abs = abs(current_value) if current_value != 0 else abs(entry_value)
    if current_abs == 0:
        current_abs = 1.0

    if strategy == "vertical_spread":
        directional_component = current_abs * (underlying_ret * directional_weight_vertical * 4.0)
        vol_component = current_abs * (vol_factor * 0.50)
        theta_component = -current_abs * (theta_factor * 0.35)

        delta_value = directional_component + vol_component + theta_component
        new_value = current_value + delta_value

        max_profit = safe_float(position.get("structure", {}).get("max_profit", 0.0), 0.0)
        max_loss = safe_float(position.get("structure", {}).get("max_loss", estimated_risk_eur), estimated_risk_eur)

        new_value = clamp(new_value, -max_loss, max_profit)
        pnl_eur = new_value - entry_value

    elif strategy in {"covered_call", "cash_secured_put"}:
        theta_component = current_abs * theta_factor
        directional_component = current_abs * (underlying_ret * directional_weight_short_premium)
        vol_component = -current_abs * (vol_factor * 0.35)

        delta_value = -(theta_component + vol_component) + directional_component
        new_value = current_value + delta_value
        new_value = max(new_value, 0.0)

        pnl_eur = entry_value - new_value

    else:
        new_value = current_value
        pnl_eur = 0.0

    days_in_trade += 1
    days_to_expiry = max(days_to_expiry - 1, 0)

    entry_abs = abs(entry_value) if entry_value != 0 else 1.0
    pnl_pct = (pnl_eur / entry_abs) * 100.0

    position["pricing_model"] = "v2_simplified_repricing"
    position["last_reprice_ts"] = utc_now_iso()
    position["underlying_return_simulated"] = round(underlying_ret, 6)
    position["theta_factor_applied"] = round(theta_factor, 6)
    position["vol_factor_applied"] = round(vol_factor, 6)
    position["current_value_eur"] = round(new_value, 2)
    position["days_in_trade"] = days_in_trade
    position["days_to_expiry"] = days_to_expiry
    position["pnl_eur"] = round(pnl_eur, 2)
    position["pnl_pct"] = round(pnl_pct, 2)

    return position
