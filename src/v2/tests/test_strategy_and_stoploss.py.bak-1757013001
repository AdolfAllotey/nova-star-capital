import sys
import os

# Ajout du dossier src/v2 au PYTHONPATH pour imports relatifs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.dynamic_stop_loss import DynamicStopLoss
from core.strategy_engine import apply_strategy

def test_dynamic_stop_loss():
    print("=== Test DynamicStopLoss ===")
    prices_list = [
        [100, 102, 105, 103, 107, 110, 108, 107, 111, 115],
        [50, 48, 47, 46, 45, 44, 43, 42, 41, 40],
        [10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    ]

    for i, prices in enumerate(prices_list, 1):
        dsl = DynamicStopLoss(prices, min_stop_pct=0.1, lookback=5)
        stop = dsl.calculate_stop_loss()
        current = prices[-1]
        decision = "SELL" if dsl.should_sell(current, stop) else "HOLD"
        print(f"Test {i}: Current price={current}, Stop loss={stop:.2f}, Decision={decision}")

def test_strategy_engine():
    print("\n=== Test Strategy Engine ===")
    tokens = [
        {"symbol": "AAA", "score": 90, "sentiment": 0.7, "category": "layer1", "price_history": [100, 102, 101, 105, 107]},
        {"symbol": "BBB", "score": 60, "sentiment": 0.1, "category": "memecoin", "price_history": [0.01, 0.009, 0.008, 0.007, 0.006]},
        {"symbol": "CCC", "score": 75, "sentiment": 0.4, "category": "layer2", "price_history": [50, 51, 52, 53, 54]},
    ]

    strategy_rules = [
        {
            "name": "High score buy",
            "conditions": [{"field": "score", "op": ">", "value": 80}],
            "action": "buy"
        },
        {
            "name": "Low sentiment sell",
            "conditions": [{"field": "sentiment", "op": "<", "value": 0.2}],
            "action": "sell"
        }
    ]

    actions = apply_strategy(tokens, strategy_rules)
    for action in actions:
        print(f"Action recommandée: {action['action']} {action['symbol']} ({action['reason']})")

if __name__ == "__main__":
    test_dynamic_stop_loss()
    test_strategy_engine()