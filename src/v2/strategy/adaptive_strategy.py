
import json
import os
from datetime import datetime, timezone, timezone

STRATEGY_FILE = "data/v2/strategies/active_strategy.json"
HISTORY_FILE = "data/v2/strategies/strategy_history.json"
os.makedirs(os.path.dirname(STRATEGY_FILE), exist_ok=True)

DEFAULT_STRATEGY = {
    "name": "standard",
    "risk_level": "medium",
    "allocation_multiplier": 1.0
}

def load_strategy():
    if os.path.exists(STRATEGY_FILE):
        with open(STRATEGY_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_STRATEGY

def save_strategy(strategy):
    with open(STRATEGY_FILE, "w") as f:
        json.dump(strategy, f, indent=2)

def log_strategy_change(old, new):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "old": old,
        "new": new
    }
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    history.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def adapt_strategy(performance: dict):
    strategy = load_strategy()
    old_strategy = strategy.copy()
    pnl = performance.get("total_pnl", 0)
    roi = performance.get("roi_pct", 0)

    if roi > 10:
        strategy["risk_level"] = "high"
        strategy["allocation_multiplier"] = 1.2
        strategy["name"] = "aggressive"
    elif roi < -5:
        strategy["risk_level"] = "low"
        strategy["allocation_multiplier"] = 0.5
        strategy["name"] = "defensive"
    else:
        strategy["risk_level"] = "medium"
        strategy["allocation_multiplier"] = 1.0
        strategy["name"] = "standard"

    if strategy != old_strategy:
        log_strategy_change(old_strategy, strategy)
        save_strategy(strategy)
        print(f"🔁 Nouvelle stratégie appliquée : {strategy}")
    else:
        print("✅ Stratégie inchangée.")

if __name__ == "__main__":
    sample_perf = {"total_pnl": 800, "roi_pct": 11}
    adapt_strategy(sample_perf)
