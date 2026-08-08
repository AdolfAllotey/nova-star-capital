#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.portfolio.budget_context import load_budget_context


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore

        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default

        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore

        save_json_file(str(path), data)
    except Exception:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(
                data,
                handle,
                ensure_ascii=False,
                indent=2,
            )


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass
class RiskParams:
    max_positions: int = 5
    max_new_entries_per_run: int = 2
    per_trade_risk_pct: float = 0.05
    min_trade_usd: float = 200.0
    max_trade_usd: float = 25_000.0
    min_meta_score: float = 60.0


def soft_veto_from_regime(regime: str) -> Tuple[bool, str]:
    if regime == "risk_off":
        return True, "risk_off_exit_only"

    return False, ""



def risk_decide_one(
    sig: Dict[str, Any],
    inputs: Dict[str, Any],
    params: RiskParams,
) -> Dict[str, Any]:
    symbol = sig.get("symbol")
    meta_score = float(sig.get("meta_score") or 0.0)

    budget_context = inputs.get("budget_context") or {}

    try:
        budget_usd = float(
            budget_context.get("budget_usd") or 0.0
        )
    except Exception:
        budget_usd = 0.0

    try:
        budget_eur = float(
            budget_context.get("budget_eur") or 0.0
        )
    except Exception:
        budget_eur = 0.0

    budget_status = str(
        budget_context.get("status") or "blocked"
    )

    regime = (
        (inputs.get("market_regime") or {}).get("regime")
        or "neutral"
    )

    allowed = True
    vetos: List[Dict[str, Any]] = []

    if budget_status != "ok":
        allowed = False
        vetos.append(
            {
                "type": "budget_contract_invalid",
                "severity": "hard",
                "reason": (
                    budget_context.get("error")
                    or "portfolio_fx_budget_unavailable"
                ),
            }
        )

    if budget_usd <= 0:
        allowed = False
        vetos.append(
            {
                "type": "budget_zero",
                "severity": "hard",
                "reason": "canonical budget_usd <= 0",
            }
        )

    if meta_score < params.min_meta_score:
        allowed = False
        vetos.append(
            {
                "type": "meta_score_low",
                "severity": "hard",
                "reason": (
                    f"meta_score<{params.min_meta_score}"
                ),
            }
        )

    soft, reason = soft_veto_from_regime(regime)

    if soft:
        vetos.append(
            {
                "type": "regime_soft_veto",
                "severity": "soft",
                "reason": reason,
            }
        )

    size_usd = 0.0

    if allowed:
        size_usd = (
            budget_usd * params.per_trade_risk_pct
        )

        size_usd = clamp(
            size_usd,
            params.min_trade_usd,
            params.max_trade_usd,
        )

        size_usd = min(size_usd, budget_usd)

        if size_usd < params.min_trade_usd:
            allowed = False
            vetos.append(
                {
                    "type": "min_trade",
                    "severity": "hard",
                    "reason": (
                        "size_usd below min_trade_usd"
                    ),
                }
            )
            size_usd = 0.0

    fx_metadata = budget_context.get("fx")

    return {
        "ts": utc_now_iso(),
        "symbol": symbol,
        "direction": sig.get("direction"),
        "setup": sig.get("setup"),
        "engine": sig.get("engine"),
        "meta_score": meta_score,
        "allowed": bool(allowed),
        "size_usd": round(float(size_usd), 2),
        "budget": {
            "source": budget_context.get(
                "budget_source"
            ),
            "scope": budget_context.get("scope"),
            "budget_eur": round(budget_eur, 2),
            "budget_usd": round(budget_usd, 2),
            "source_currency": (
                budget_context.get("source_currency")
            ),
            "target_currency": (
                budget_context.get("target_currency")
            ),
            "status": budget_status,
        },
        "fx": fx_metadata,
        "regime": regime,
        "vetos": vetos,
        "meta": {
            "risk_engine": "risk_engine_v1",
            "version": "1.1",
            "budget_contract": (
                "portfolio_pocket_eur_to_core_fx_usd_v1"
            ),
        },
    }


def run_risk_engine(
    voted_path: str | None = None,
    inputs_path: str | None = None,
    out_decisions: str | None = None,
    out_candidates: str | None = None,
) -> Dict[str, Any]:
    root = Path(
        os.getenv(
            "NSC_DATA_DIR",
            "/opt/nsc/data/preprod",
        )
    )

    voted_path = voted_path or str(
        root
        / "equities_offensive/voting/"
        "voted_signals.json"
    )

    inputs_path = inputs_path or str(
        root / "equities_offensive/inputs.json"
    )

    out_decisions = out_decisions or str(
        root
        / "equities_offensive/risk/"
        "risk_decisions.json"
    )

    out_candidates = out_candidates or str(
        root
        / "equities_offensive/risk/"
        "execution_candidates.json"
    )

    voted_doc = (
        load_json(Path(voted_path), default={}) or {}
    )

    source_inputs = (
        load_json(Path(inputs_path), default={}) or {}
    )

    if not isinstance(source_inputs, dict):
        source_inputs = {}

    budget_context = load_budget_context(root)

    runtime_inputs = dict(source_inputs)
    runtime_inputs["budget_context"] = budget_context

    voted = voted_doc.get("voted") or []

    if not isinstance(voted, list):
        voted = []

    params = RiskParams()

    decisions = [
        risk_decide_one(
            signal,
            runtime_inputs,
            params,
        )
        for signal in voted
        if isinstance(signal, dict)
    ]

    def is_candidate(
        decision: Dict[str, Any],
    ) -> bool:
        if not decision.get("allowed"):
            return False

        for veto in decision.get("vetos") or []:
            if veto.get("severity") == "hard":
                return False

            if (
                veto.get("type")
                == "regime_soft_veto"
                and veto.get("reason")
                == "risk_off_exit_only"
            ):
                return False

        return True

    candidates = [
        decision
        for decision in decisions
        if is_candidate(decision)
    ]

    out = {
        "ts": utc_now_iso(),
        "risk_engine": "risk_engine_v1",
        "version": "1.1",
        "count_in": len(voted),
        "count_decisions": len(decisions),
        "count_candidates": len(candidates),
        "budget_context": budget_context,
        "inputs": {
            "voted_path": voted_path,
            "inputs_path": inputs_path,
            "legacy_budget_trading_ignored": (
                "budget_trading" in source_inputs
            ),
        },
        "params": {
            "max_positions": params.max_positions,
            "max_new_entries_per_run": (
                params.max_new_entries_per_run
            ),
            "per_trade_risk_pct": (
                params.per_trade_risk_pct
            ),
            "min_trade_usd": params.min_trade_usd,
            "max_trade_usd": params.max_trade_usd,
            "min_meta_score": params.min_meta_score,
        },
    }

    save_json(
        Path(out_decisions),
        {
            "ts": out["ts"],
            "decisions": decisions,
            "meta": out,
        },
    )

    save_json(
        Path(out_candidates),
        {
            "ts": out["ts"],
            "candidates": candidates,
            "meta": out,
        },
    )

    return out


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Equities Offensive Risk Engine V1.1"
        )
    )

    parser.add_argument("--voted", default=None)
    parser.add_argument("--inputs", default=None)
    parser.add_argument(
        "--out-decisions",
        default=None,
    )
    parser.add_argument(
        "--out-candidates",
        default=None,
    )

    args = parser.parse_args()

    out = run_risk_engine(
        args.voted,
        args.inputs,
        args.out_decisions,
        args.out_candidates,
    )

    print(
        json.dumps(
            out,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
