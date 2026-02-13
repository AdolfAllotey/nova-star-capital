#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def build_budgets(capital_state: Dict[str, Any]) -> Dict[str, Any]:
    budgets = (capital_state or {}).get("budgets", {}) or {}
    targets = budgets.get("targets", {}) or {}
    weights = budgets.get("weights", {}) or {}

    # Canonical budgets for orchestrator
    return {
        "ts": utc_now_iso(),
        "phase": (capital_state or {}).get("phase"),
        "equity": (capital_state or {}).get("equity"),
        "cash": (capital_state or {}).get("cash"),
        "tax_reserved": (capital_state or {}).get("tax_reserved"),
        "targets": {
            "trading": float(targets.get("trading", 0.0)),
            "lt": float(targets.get("lt", 0.0))
        },
        "weights": weights
    }

def build_inputs_for_equities_offensive(budgets: Dict[str, Any], governance: Dict[str, Any], market_regime: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": utc_now_iso(),
        "module": "equities_offensive",
        "budget_trading": budgets["targets"]["trading"],
        "phase": budgets.get("phase"),
        "mode": governance.get("mode"),
        "action_policy": governance.get("action_policy"),
        "caps": governance.get("caps", {}),
        "market_regime": market_regime
    }

def build_inputs_for_lt_global_equity(budgets: Dict[str, Any], governance: Dict[str, Any], market_regime: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": utc_now_iso(),
        "module": "lt_global_equity",
        "budget_lt": budgets["targets"]["lt"],
        "phase": budgets.get("phase"),
        "mode": governance.get("mode"),
        "action_policy": governance.get("action_policy"),
        "caps": governance.get("caps", {}),
        "market_regime": market_regime
    }

def route_budgets(
    *,
    capital_state_path: str = "data/capital/capital_state.json",
    governance_path: str = None,
    market_regime_path: str = "data/market/market_regime_actions.json",
    out_budgets_path: str = "data/orchestrator/budgets.json",
    out_equities_inputs: str = "data/equities_offensive/inputs.json",
    out_lt_inputs: str = "data/lt_global_equity/inputs.json"
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    # Load inputs
    capital_state = load_json(Path(capital_state_path), default={}) or {}

    # Governance loader (single source)
    if governance_path:
        governance = load_json(Path(governance_path), default={}) or {}
    else:
        from src.v2.governance.governance_loader import load_governance  # type: ignore
        governance = load_governance()

    market_regime = load_json(Path(market_regime_path), default={}) or {}

    budgets = build_budgets(capital_state)

    equities_inputs = build_inputs_for_equities_offensive(budgets, governance, market_regime)
    lt_inputs = build_inputs_for_lt_global_equity(budgets, governance, market_regime)

    save_json(Path(out_budgets_path), budgets)
    save_json(Path(out_equities_inputs), equities_inputs)
    save_json(Path(out_lt_inputs), lt_inputs)

    return budgets, equities_inputs, lt_inputs

# --- CLI

def main():
    import argparse
    ap = argparse.ArgumentParser(description="NSC Budget Router (capital_state -> module inputs)")
    ap.add_argument("--capital-state", default="data/capital/capital_state.json")
    ap.add_argument("--market-regime", default="data/market/market_regime_actions.json")
    ap.add_argument("--out-budgets", default="data/orchestrator/budgets.json")
    ap.add_argument("--out-equities", default="data/equities_offensive/inputs.json")
    ap.add_argument("--out-lt", default="data/lt_global_equity/inputs.json")
    ap.add_argument("--governance", default="", help="Optional governance path override")
    args = ap.parse_args()

    budgets, equities_inputs, lt_inputs = route_budgets(
        capital_state_path=args.capital_state,
        governance_path=(args.governance.strip() or None),
        market_regime_path=args.market_regime,
        out_budgets_path=args.out_budgets,
        out_equities_inputs=args.out_equities,
        out_lt_inputs=args.out_lt
    )

    print("OK budgets -> inputs")
    print("budgets:", args.out_budgets)
    print("equities:", args.out_equities)
    print("lt:", args.out_lt)

if __name__ == "__main__":
    main()
