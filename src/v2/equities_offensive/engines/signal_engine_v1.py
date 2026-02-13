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
class EngineWeights:
    trend: float = 0.35
    breakout: float = 0.25
    retest: float = 0.15
    continuation: float = 0.15
    volume: float = 0.10

def trend_score(px: Dict[str, Any]) -> float:
    c = float(px.get("close") or 0)
    ma20 = float(px.get("ma20") or 0)
    ma50 = float(px.get("ma50") or 0)
    ma200 = float(px.get("ma200") or 0)
    s = 0.0
    if c > ma20: s += 0.25
    if ma20 > ma50: s += 0.25
    if ma50 > ma200: s += 0.50
    return clamp(s, 0, 1)

def breakout_score(px: Dict[str, Any]) -> float:
    c = float(px.get("close") or 0)
    hh = float(px.get("hh_20") or 0)
    if hh <= 0: return 0.0
    # close near/above 20d high
    dist = (c - hh) / hh
    # 0 when 2% below, 1 when at/above
    return clamp((dist + 0.02) / 0.02, 0, 1)

def retest_score(px: Dict[str, Any]) -> float:
    c = float(px.get("close") or 0)
    ma20 = float(px.get("ma20") or 0)
    if ma20 <= 0: return 0.0
    dist = abs(c - ma20) / ma20
    # best when within 0.5% of MA20
    return clamp(1 - (dist / 0.005), 0, 1)

def continuation_score(px: Dict[str, Any]) -> float:
    ret20 = float(px.get("ret_20") or 0.0)
    # 0 at -5%, 1 at +10%
    return clamp((ret20 + 0.05) / 0.15, 0, 1)

def volume_score(px: Dict[str, Any]) -> float:
    vr = float(px.get("vol_ratio") or 1.0)
    # 1.0 => 0.3 ; 1.5 => 0.8 ; 2.0 => 1.0
    return clamp((vr - 0.8) / 1.2, 0, 1)

def score_symbol(px: Dict[str, Any], w: EngineWeights) -> Dict[str, Any]:
    t = trend_score(px)
    b = breakout_score(px)
    r = retest_score(px)
    c = continuation_score(px)
    v = volume_score(px)

    raw = (
        w.trend * t +
        w.breakout * b +
        w.retest * r +
        w.continuation * c +
        w.volume * v
    )
    score_0_100 = round(clamp(raw, 0, 1) * 100, 2)

    # classify setup
    setup = "breakout" if b >= max(r, c) else ("retest" if r >= max(b, c) else "continuation")

    return {
        "setup": setup,
        "score": score_0_100,
        "components": {
            "trend": round(t, 3),
            "breakout": round(b, 3),
            "retest": round(r, 3),
            "continuation": round(c, 3),
            "volume": round(v, 3)
        }
    }

def generate_signals(
    universe_path: str = "data/equities_offensive/universe/universe_filtered.json",
    price_snapshot_path: str = "data/equities_offensive/universe/price_snapshot.json",
    out_path: str = "data/equities_offensive/signals/signals_v1.json",
    min_score: float = 60.0
) -> Dict[str, Any]:
    uni = load_json(Path(universe_path), default={}) or {}
    pxdoc = load_json(Path(price_snapshot_path), default={}) or {}

    symbols: List[str] = uni.get("symbols") or []
    prices: Dict[str, Any] = pxdoc.get("prices") or {}

    w = EngineWeights()
    signals = []
    skipped = {}

    for sym in symbols:
        px = prices.get(sym)
        if not px:
            skipped[sym] = "missing_price_features"
            continue
        s = score_symbol(px, w)
        if s["score"] < min_score:
            skipped[sym] = f"score_below_min<{min_score}"
            continue

        signals.append({
            "ts": utc_now_iso(),
            "engine": "signal_engine_v1",
            "symbol": sym,
            "direction": "long",
            "timeframe": "D1",
            "score": s["score"],
            "setup": s["setup"],
            "features": {
                **(s["components"]),
                "close": px.get("close"),
                "ma20": px.get("ma20"),
                "ma50": px.get("ma50"),
                "ma200": px.get("ma200"),
                "hh_20": px.get("hh_20"),
                "ret_20": px.get("ret_20"),
                "vol_ratio": px.get("vol_ratio")
            },
            "reasons": [f"setup={s['setup']}", f"score={s['score']}"],
            "meta": {"version": "1.0"}
        })

    # sort by score desc
    signals.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)

    out = {
        "ts": utc_now_iso(),
        "engine": "signal_engine_v1",
        "universe": uni.get("universe"),
        "min_score": min_score,
        "count_in": len(symbols),
        "count_out": len(signals),
        "signals": signals,
        "skipped": skipped,
        "weights": {
            "trend": w.trend,
            "breakout": w.breakout,
            "retest": w.retest,
            "continuation": w.continuation,
            "volume": w.volume
        }
    }
    save_json(Path(out_path), out)
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Equities Offensive Signal Engine V1 (Nasdaq)")
    ap.add_argument("--universe", default="data/equities_offensive/universe/universe_filtered.json")
    ap.add_argument("--prices", default="data/equities_offensive/universe/price_snapshot.json")
    ap.add_argument("--out", default="data/equities_offensive/signals/signals_v1.json")
    ap.add_argument("--min-score", type=float, default=60.0)
    args = ap.parse_args()

    out = generate_signals(args.universe, args.prices, args.out, args.min_score)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
