#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

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

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

@dataclass
class RiskParams:
    max_positions: int = 5
    max_new_entries_per_run: int = 2
    per_trade_risk_pct: float = 0.05      # 5% budget/trade (V1)
    min_trade_usd: float = 200.0
    max_trade_usd: float = 25_000.0
    min_meta_score: float = 60.0

def soft_veto_from_regime(regime: str) -> Tuple[bool, str]:
    """
    Simple: en risk_off on bloque les entrées (exit-only plus tard).
    """
    if regime == "risk_off":
        return True, "risk_off_exit_only"
    return False, ""

def risk_decide_one(
    sig: Dict[str, Any],
    inputs: Dict[str, Any],
    params: RiskParams
) -> Dict[str, Any]:
    symbol = sig.get("symbol")
    meta_score = float(sig.get("meta_score") or 0.0)

    budget = float(inputs.get("budget_trading") or 0.0)
    regime = ((inputs.get("market_regime") or {}).get("regime")) or "neutral"

    # base checks
    allowed = True
    vetos: List[Dict[str, Any]] = []

    if budget <= 0:
        allowed = False
        vetos.append({"type": "budget_zero", "severity": "hard", "reason": "budget_trading <= 0"})

    if meta_score < params.min_meta_score:
        allowed = False
        vetos.append({"type": "meta_score_low", "severity": "hard", "reason": f"meta_score<{params.min_meta_score}"})

    soft, reason = soft_veto_from_regime(regime)
    if soft:
        # Soft veto (Option A: simulated_only en PREPROD sera appliqué par governance_engine)
        vetos.append({"type": "regime_soft_veto", "severity": "soft", "reason": reason})

    # sizing (V1)
    size_usd = 0.0
    if allowed:
        size_usd = budget * params.per_trade_risk_pct
        size_usd = clamp(size_usd, params.min_trade_usd, params.max_trade_usd)

        # if still bigger than budget, clamp
        size_usd = min(size_usd, budget)

        if size_usd < params.min_trade_usd:
            allowed = False
            vetos.append({"type": "min_trade", "severity": "hard", "reason": "size_usd below min_trade_usd"})
            size_usd = 0.0

    return {
        "ts": utc_now_iso(),
        "symbol": symbol,
        "direction": sig.get("direction"),
        "setup": sig.get("setup"),
        "engine": sig.get("engine"),
        "meta_score": meta_score,
        "allowed": bool(allowed),
        "size_usd": round(float(size_usd), 2),
        "regime": regime,
        "vetos": vetos,
        "meta": {
            "risk_engine": "risk_engine_v1",
            "version": "1.0"
        }
    }

def run_risk_engine(
    voted_path: str = "data/equities_offensive/voting/voted_signals.json",
    inputs_path: str = "data/equities_offensive/inputs.json",
    out_decisions: str = "data/equities_offensive/risk/risk_decisions.json",
    out_candidates: str = "data/equities_offensive/risk/execution_candidates.json"
) -> Dict[str, Any]:
    voted_doc = load_json(Path(voted_path), default={}) or {}
    inputs = load_json(Path(inputs_path), default={}) or {}

    voted = voted_doc.get("voted") or []

    params = RiskParams()
    decisions = [risk_decide_one(sig, inputs, params) for sig in voted]

    # candidates: allowed AND no hard veto
    def is_candidate(d: Dict[str, Any]) -> bool:
        if not d.get("allowed"):
            return False
        for v in d.get("vetos") or []:
            if v.get("severity") == "hard":
                return False
        return True

    candidates = [d for d in decisions if is_candidate(d)]
    # limit new entries per run
    candidates = candidates[: params.max_new_entries_per_run]

    out = {
        "ts": utc_now_iso(),
        "risk_engine": "risk_engine_v1",
        "count_in": len(voted),
        "count_decisions": len(decisions),
        "count_candidates": len(candidates),
        "params": {
            "max_positions": params.max_positions,
            "max_new_entries_per_run": params.max_new_entries_per_run,
            "per_trade_risk_pct": params.per_trade_risk_pct,
            "min_trade_usd": params.min_trade_usd,
            "max_trade_usd": params.max_trade_usd,
            "min_meta_score": params.min_meta_score
        }
    }

    save_json(Path(out_decisions), {"ts": out["ts"], "decisions": decisions, "meta": out})
    save_json(Path(out_candidates), {"ts": out["ts"], "candidates": candidates, "meta": out})

    return out

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Equities Offensive Risk Engine V1")
    ap.add_argument("--voted", default="data/equities_offensive/voting/voted_signals.json")
    ap.add_argument("--inputs", default="data/equities_offensive/inputs.json")
    ap.add_argument("--out-decisions", default="data/equities_offensive/risk/risk_decisions.json")
    ap.add_argument("--out-candidates", default="data/equities_offensive/risk/execution_candidates.json")
    args = ap.parse_args()

    out = run_risk_engine(args.voted, args.inputs, args.out_decisions, args.out_candidates)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
