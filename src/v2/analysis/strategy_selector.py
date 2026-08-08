from pathlib import Path
from datetime import datetime, timezone
import json

DATA_DIR = Path("/opt/nsc/data/preprod")
PERF = DATA_DIR / "analysis" / "strategy_performance.json"
OUT = DATA_DIR / "analysis" / "strategy_weights.json"

STRATEGIES = ["momentum", "breakout", "whale", "sniper"]
MIN_TRADES = 10

def load_json(path, default):
    try:
        if path.exists() and path.stat().st_size > 0:
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def score_strategy(s):
    trades = int(s.get("trades", 0) or 0)
    winrate = float(s.get("winrate", 0.0) or 0.0)
    pnl_avg = float(s.get("pnl_avg", 0.0) or 0.0)
    pf = s.get("profit_factor")

    if trades < MIN_TRADES:
        return 0.5, "neutral:not_enough_trades"

    if pf is None:
        # Garde-fou anti overfit: aucune perte observée = dataset incomplet.
        return 0.5, "neutral:no_losses_yet"

    pf = float(pf)

    pf_score = clamp((pf - 1.0) / 1.0, 0.0, 1.0)
    pnl_score = 1.0 if pnl_avg > 0 else 0.0
    score = (0.45 * winrate) + (0.35 * pf_score) + (0.20 * pnl_score)

    if score >= 0.75:
        label = "boost"
    elif score <= 0.40:
        label = "reduce"
    else:
        label = "neutral"

    return round(score, 4), label

def weight_from_score(score, label):
    if label == "boost":
        return 1.15
    if label == "reduce":
        return 0.75
    return 1.0

def main():
    perf = load_json(PERF, {})
    by_strategy = perf.get("by_strategy", {}) if isinstance(perf, dict) else {}

    weights = {}
    diagnostics = {}

    for strat in STRATEGIES:
        s = by_strategy.get(strat, {})
        score, label = score_strategy(s)
        weights[strat] = weight_from_score(score, label)
        diagnostics[strat] = {
            "score": score,
            "label": label,
            "trades": s.get("trades", 0),
            "winrate": s.get("winrate"),
            "pnl_avg": s.get("pnl_avg"),
            "profit_factor": s.get("profit_factor")
        }

    payload = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "engine": "strategy_selector_v1",
        "min_trades": MIN_TRADES,
        "weights": weights,
        "diagnostics": diagnostics,
        "source": str(PERF)
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
