from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from src.v2.utils.file_utils import get_data_dir


def _get_data_dir() -> Path:
    return get_data_dir()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _safe_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def main() -> Dict[str, Any]:
    data_dir = _get_data_dir()
    trading_dir = data_dir / "trading"
    analysis_dir = data_dir / "analysis"

    capital_config_path = trading_dir / "capital_config.json"
    market_regime_path = analysis_dir / "market_regime_detector.json"
    output_path = trading_dir / "capital_allocation.json"

    capital_config = _read_json(capital_config_path, {}) or {}
    market_regime = _read_json(market_regime_path, {}) or {}

    # Legacy portfolio-observation contract only.
    #
    # These are NOT the dynamic Strategy Selector V2 weights.  The selector
    # emits sizing multipliers in analysis/strategy_weights.json and is
    # consumed independently by position sizing.
    #
    # Keep the historical three-strategy allocation explicit for V1
    # compatibility without pretending it came from a runtime authority.
    strategy_weights = {
        "momentum": 1 / 3,
        "sniper": 1 / 3,
        "whale": 1 / 3,
    }

    total_budget = _safe_float(capital_config.get("total_budget"), 1000.0)
    trading_ratio = _safe_float(capital_config.get("trading_ratio"), 0.45)
    max_positions = int(capital_config.get("max_positions", 10) or 10)

    regime = str(market_regime.get("regime") or "neutral")
    # Emotional governance is handled by its dedicated governance engines.
    # capital_allocation.json is not an emotional-state authority.
    emotional_regime_name = "not_applicable"
    emotional_action = "not_applicable"

    trading_budget = round(total_budget * trading_ratio, 2)
    capital_per_trade = round(trading_budget / max_positions, 2) if max_positions > 0 else 0.0

    strategy_budgets = {
        k: round(trading_budget * float(v), 2)
        for k, v in strategy_weights.items()
    }

    result = {
        "regime": regime,
        "emotional_regime": emotional_regime_name,
        "action": "normal",
        "emotional_action": emotional_action,
        "total_capital": total_budget,
        "pockets": {
            "trading": trading_budget
        },
        "max_concurrent_positions": max_positions,
        "total_budget": total_budget,
        "trading_budget": trading_budget,
        "trading_ratio": trading_ratio,
        "capital_per_trade": capital_per_trade,
        "max_positions": max_positions,
        "strategy_weights": strategy_weights,
        "strategy_budgets": strategy_budgets,
        "config_source": str(capital_config_path),
        "market_regime_source": str(market_regime_path),
        "emotional_regime_source": "not_applicable_to_capital_allocator",
        "strategy_weights_source": "static_v1_legacy_portfolio_observation_contract",
    }

    _write_json(output_path, result)
    print(f"[capital_allocator] capital_allocation.json sauvegardé: {output_path}")

    return result


if __name__ == "__main__":
    main()
