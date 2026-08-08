#!/usr/bin/env python3
from __future__ import annotations


def _extract_inputs_from_snapshot(snapshot: dict) -> dict:
    """Support 2 formats:
    A) snapshot direct: {vix, qqq_trend, spy_trend, breadth_pct_above_ma200, aggregate_score?}
    B) NSC market_snapshot_exporter: {timestamp, env, sources:{market_conditions, ...}}
    """

    if not isinstance(snapshot, dict):
        snapshot = {}

    # ---------- Format A (direct) ----------
    has_direct = any(k in snapshot for k in ("vix", "qqq_trend", "spy_trend", "breadth_pct_above_ma200", "aggregate_score"))
    if has_direct:
        def _f(x, default=0.0):
            try:
                if x is None:
                    return default
                return float(x)
            except Exception:
                return default

        return {
            "vix": _f(snapshot.get("vix", 0.0), 0.0),
            "qqq_trend": _f(snapshot.get("qqq_trend", 0.0), 0.0),
            "spy_trend": _f(snapshot.get("spy_trend", 0.0), 0.0),
            "breadth_pct_above_ma200": snapshot.get("breadth_pct_above_ma200", None),
            "aggregate_score": _f(snapshot.get("aggregate_score", 0.0), 0.0),
        }

    # ---------- Format B (market_snapshot_exporter) ----------
    sources = snapshot.get("sources") or {}
    mc = sources.get("market_conditions") or {}

    regime = (mc.get("regime") or "neutral").lower()
    score = mc.get("score", None)
    gflag = (mc.get("global_flag") or "").lower()

    # Valeurs par défaut
    vix = 0.0
    qqq_trend = 0.0
    spy_trend = 0.0
    breadth = None
    aggregate_score = 0.0

    # Si market_conditions a un bloc inputs, on l'utilise en priorité
    mc_inputs = mc.get("inputs") or {}
    if isinstance(mc_inputs, dict) and mc_inputs:
        try:
            vix = float(mc_inputs.get("vix", 0.0) or 0.0)
        except Exception:
            vix = 0.0
        try:
            qqq_trend = float(mc_inputs.get("qqq_trend", 0.0) or 0.0)
        except Exception:
            qqq_trend = 0.0
        try:
            spy_trend = float(mc_inputs.get("spy_trend", 0.0) or 0.0)
        except Exception:
            spy_trend = 0.0
        breadth = mc_inputs.get("breadth_pct_above_ma200", None)
        try:
            aggregate_score = float(mc_inputs.get("aggregate_score", 0.0) or 0.0)
        except Exception:
            aggregate_score = 0.0
    else:
        # Heuristique simple pour ne pas sortir 0 partout
        if regime == "bull":
            qqq_trend = 1.0
            spy_trend = 1.0
        elif regime == "bear":
            qqq_trend = -1.0
            spy_trend = -1.0

        if isinstance(score, (int, float)):
            breadth = float(score)
            aggregate_score = float(score)

    return {
        "vix": vix,
        "qqq_trend": qqq_trend,
        "spy_trend": spy_trend,
        "breadth_pct_above_ma200": breadth,
        "aggregate_score": aggregate_score,
        "market_conditions_regime": regime,
        "market_conditions_score": score,
        "market_conditions_global_flag": gflag,
    }

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Helpers

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any = None) -> Any:
    try:
        # Prefer project helper if available
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
class RegimeResult:
    regime: str
    confidence: float
    reasons: List[str]
    inputs: Dict[str, Any]



def compute_confidence_score(
    agg: float,
    vix: float,
    qqq: dict,
    spy: dict,
    breadth: dict,
) -> float:
    """
    Confidence = conviction exploitable, pas simple direction du score.
    On pénalise les inputs manquants pour éviter NEUTRAL / 100%.
    """
    base = min(1.0, abs(float(agg or 0.0)))

    penalty = 0.0

    if not vix or vix <= 0:
        penalty += 0.30

    if not isinstance(qqq, dict) or not qqq.get("close") or not qqq.get("ma50") or not qqq.get("ma200"):
        penalty += 0.25

    if not isinstance(spy, dict) or not spy.get("close") or not spy.get("ma50") or not spy.get("ma200"):
        penalty += 0.25

    if not isinstance(breadth, dict) or breadth.get("pct_above_ma200") is None:
        penalty += 0.10

    return round(max(0.0, min(1.0, base - penalty)), 4)

# --- Core logic

def detect_market_regime(snapshot: Dict[str, Any] | None = None) -> RegimeResult:
    # PREPROD-safe: allow snapshot to be None/missing
    if snapshot is None:
        snapshot = {}

    inputs = _extract_inputs_from_snapshot(snapshot)
    """
    Expected snapshot fields (best effort):
    {
      "ts": "...",
      "vix": 14.2,
      "qqq": {"close": 420.1, "ma50": 410.0, "ma200": 380.0, "ret_20d": 0.06},
      "spy": {"close": 505.0, "ma50": 498.0, "ma200": 470.0, "ret_20d": 0.04},
      "breadth": {"pct_above_ma200": 0.62}  # optional
    }
    """

    vix = float(inputs.get("vix", 0.0) or 0.0)
    qqq = snapshot.get("qqq") or {}
    spy = snapshot.get("spy") or {}
    breadth = snapshot.get("breadth") or {}

    def trend_score(x: Dict[str, Any], label: str) -> Tuple[float, List[str]]:
        reasons = []
        close = float(x.get("close") or 0.0)
        ma50 = float(x.get("ma50") or 0.0)
        ma200 = float(x.get("ma200") or 0.0)
        ret_20d = float(x.get("ret_20d") or 0.0)

        score = 0.0

        if close > 0 and ma50 > 0:
            if close >= ma50:
                score += 0.35
                reasons.append(f"{label}: close>=MA50")
            else:
                score -= 0.35
                reasons.append(f"{label}: close<MA50")

        if close > 0 and ma200 > 0:
            if close >= ma200:
                score += 0.35
                reasons.append(f"{label}: close>=MA200")
            else:
                score -= 0.35
                reasons.append(f"{label}: close<MA200")

        # Momentum 20d (cap)
        if ret_20d != 0.0:
            if ret_20d >= 0:
                score += clamp(ret_20d / 0.10, 0.0, 0.30)  # up to +0.30
                reasons.append(f"{label}: ret_20d positive")
            else:
                score -= clamp(abs(ret_20d) / 0.10, 0.0, 0.30)  # down to -0.30
                reasons.append(f"{label}: ret_20d negative")

        return clamp(score, -1.0, 1.0), reasons

    qqq_trend, qqq_reasons = trend_score(qqq, "QQQ")
    spy_trend, spy_reasons = trend_score(spy, "SPY")

    # Breadth proxy (optional)
    pct_above = breadth.get("pct_above_ma200", None)
    breadth_score = 0.0
    breadth_reason = None
    if pct_above is not None:
        pct_above = float(pct_above)
        if pct_above >= 0.60:
            breadth_score = 0.20
            breadth_reason = "Breadth strong (>=60% above MA200)"
        elif pct_above <= 0.40:
            breadth_score = -0.20
            breadth_reason = "Breadth weak (<=40% above MA200)"
        else:
            breadth_score = 0.0
            breadth_reason = "Breadth neutral"

    # Volatility gate via VIX (simple tiers)
    vol_score = 0.0
    vol_reason = "VIX missing/0"
    if vix > 0:
        if vix <= 16:
            vol_score = 0.30
            vol_reason = "VIX low (<=16)"
        elif vix <= 22:
            vol_score = 0.10
            vol_reason = "VIX moderate (16-22)"
        elif vix <= 30:
            vol_score = -0.15
            vol_reason = "VIX elevated (22-30)"
        else:
            vol_score = -0.30
            vol_reason = "VIX high (>30)"

    # Aggregate
    # Weight Nasdaq (QQQ) slightly more for Actions Offensives
    agg = (0.45 * qqq_trend) + (0.35 * spy_trend) + breadth_score + vol_score

    reasons = []
    reasons += qqq_reasons
    reasons += spy_reasons
    if breadth_reason:
        reasons.append(breadth_reason)
    reasons.append(vol_reason)

    # Regime thresholds
    if agg >= 0.45:
        regime = "risk_on"
    elif agg <= -0.35:
        regime = "risk_off"
    else:
        regime = "neutral"

    conf = float(abs(agg))
    if regime == "neutral":
        conf = max(0.4, 1.0 - min(1.0, abs(agg) / 0.45))

    if conf < 0.4:
        conf = 0.4

    return RegimeResult(regime=regime, confidence=float(conf), reasons=reasons, inputs=inputs)
def write_market_regime(snapshot_path: str, out_path: str) -> Dict[str, Any]:
    snap = load_json(Path(snapshot_path), default={}) or {}
    res = detect_market_regime(snap)

    out = {
        "ts": utc_now_iso(),
        "regime": res.regime,
        "confidence": round(res.confidence, 4),
        "reasons": res.reasons[:25],
        "inputs": res.inputs
    }
    save_json(Path(out_path), out)
    return out

# --- CLI

def main():
    import argparse
    ap = argparse.ArgumentParser(description="NSC Market Regime Detector (V1)")
    ap.add_argument("--snapshot", required=True, help="Path to market snapshot JSON")
    ap.add_argument("--out", default="data/market/market_regime_actions.json", help="Output JSON path")
    args = ap.parse_args()

    out = write_market_regime(args.snapshot, args.out)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
