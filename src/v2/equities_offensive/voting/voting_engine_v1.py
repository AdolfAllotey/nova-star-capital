#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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

@dataclass
class EngineVoteWeight:
    engine: str
    weight: float

# V1: un seul moteur, mais structure prête pour multi-engines
ENGINE_WEIGHTS = [
    EngineVoteWeight(engine="signal_engine_v1", weight=1.0)
]

def compute_meta_score(signal: Dict[str, Any]) -> float:
    """
    Meta-score simple V1 :
    - score engine (0-100)
    - bonus setup
    """
    base = float(signal.get("score", 0.0))

    setup = signal.get("setup")
    bonus = 0.0
    if setup == "breakout":
        bonus = 5.0
    elif setup == "retest":
        bonus = 3.0
    elif setup == "continuation":
        bonus = 2.0

    return round(base + bonus, 2)

def vote_signals(
    signals_path: str = "data/equities_offensive/signals/signals_v1.json",
    out_voted: str = "data/equities_offensive/voting/voted_signals.json",
    out_explain: str = "data/equities_offensive/voting/voting_explain.json",
    top_k: int = 5
) -> Dict[str, Any]:

    doc = load_json(Path(signals_path), default={}) or {}
    signals: List[Dict[str, Any]] = doc.get("signals") or []

    voted = []
    explain = {}

    for sig in signals:
        engine = sig.get("engine")
        weight = next((w.weight for w in ENGINE_WEIGHTS if w.engine == engine), 0.0)

        meta_score = compute_meta_score(sig) * weight

        entry = {
            "symbol": sig["symbol"],
            "direction": sig["direction"],
            "setup": sig["setup"],
            "engine": engine,
            "engine_score": sig["score"],
            "meta_score": meta_score,
            "timeframe": sig.get("timeframe"),
            "ts": sig.get("ts")
        }
        voted.append(entry)

        explain[sig["symbol"]] = {
            "engine": engine,
            "engine_score": sig["score"],
            "engine_weight": weight,
            "setup": sig["setup"],
            "setup_bonus": meta_score - sig["score"],
            "final_meta_score": meta_score,
            "reasons": sig.get("reasons", [])
        }

    # sort & top-K
    voted.sort(key=lambda x: float(x.get("meta_score", 0.0)), reverse=True)
    top = voted[:top_k]

    out = {
        "ts": utc_now_iso(),
        "voting_engine": "voting_engine_v1",
        "count_in": len(voted),
        "count_out": len(top),
        "top_k": top_k,
        "voted": top
    }

    save_json(Path(out_voted), out)
    save_json(Path(out_explain), {
        "ts": utc_now_iso(),
        "engine": "voting_engine_v1",
        "details": explain
    })

    return out

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Equities Offensive Voting Engine V1")
    ap.add_argument("--signals", default="data/equities_offensive/signals/signals_v1.json")
    ap.add_argument("--out", default="data/equities_offensive/voting/voted_signals.json")
    ap.add_argument("--explain", default="data/equities_offensive/voting/voting_explain.json")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    out = vote_signals(args.signals, args.out, args.explain, args.top_k)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
