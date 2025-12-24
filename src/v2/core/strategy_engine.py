import os
import json
from src.v2.core.dynamic_stop_loss import DynamicStopLoss
from src.utils.telegram_bot import send_telegram_message

STRATEGY_FOLDER = "data/v2/strategies"
STRATEGY_FILE = os.path.join(STRATEGY_FOLDER, "strategy.json")
LOG_FILE = "data/v2/logs/strategy_log.json"

os.makedirs(STRATEGY_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def load_strategy(file_path=STRATEGY_FILE):
    if not os.path.exists(file_path):
        print(f"⚠️ Fichier de stratégie introuvable : {file_path}")
        return []
    with open(file_path, "r") as f:
        return json.load(f)

def save_log(log, file_path=LOG_FILE):
    with open(file_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"✅ Log sauvegardé dans : {file_path}")

def evaluate_rule(token, rule):
    for cond in rule.get("conditions", []):
        field = cond.get("field")
        op = cond.get("op")
        val = cond.get("value")
        token_val = token.get(field)

        if token_val is None:
            return False

        if not compare(token_val, op, val):
            return False
    return True

def compare(a, op, b):
    if op == ">":
        return a > b
    elif op == "<":
        return a < b
    elif op == ">=":
        return a >= b
    elif op == "<=":
        return a <= b
    elif op == "==":
        return a == b
    elif op == "!=":
        return a != b
    else:
        return False

def calculate_quantity(token):
    """
    Placeholder pour calculer la quantité à trader.
    À adapter selon ton portefeuille et règles.
    """
    # Exemple simple : toujours 1 unité
    return 1

def apply_strategy(tokens, strategy_rules):
    actions = []
    for token in tokens:
        price_history = token.get("price_history", [])
        symbol = token.get("symbol")
        if price_history:
            dsl = DynamicStopLoss(price_history, min_stop_pct=0.1, lookback=20, vol_multiplier=1.5, method='ewma')
            stop_loss_level = dsl.calculate_stop_loss()
            current_price = price_history[-1]
            if dsl.should_sell(current_price, stop_loss_level):
                actions.append({
                    "symbol": symbol,
                    "action": "sell",
                    "reason": "stop_loss_dynamique",
                    "stop_loss_level": stop_loss_level,
                    "current_price": current_price,
                    "quantity": calculate_quantity(token)
                })
                continue  # ne pas appliquer d’autres règles si stop loss déclenché

        for rule in strategy_rules:
            if evaluate_rule(token, rule):
                action = rule.get("action")
                reason = rule.get("name")
                actions.append({
                    "symbol": symbol,
                    "action": action,
                    "reason": reason,
                    "quantity": calculate_quantity(token)
                })
                break
    return actions

def execute_trade(action):
    symbol = action["symbol"]
    act = action["action"]
    reason = action["reason"]
    quantity = action.get("quantity", 1)
    if act == "sell":
        print(f"🛑 Vente recommandée pour {symbol} ({reason}), quantité : {quantity}")
        send_telegram_message(f"🛑 Vente recommandée : {symbol} ({reason}), quantité : {quantity}")
    elif act == "buy":
        print(f"✅ Achat recommandé pour {symbol} ({reason}), quantité : {quantity}")
        send_telegram_message(f"✅ Achat recommandé : {symbol} ({reason}), quantité : {quantity}")

def main():
    strategy_rules = load_strategy()
    # Exemple tokens, remplacer par données réelles
    tokens = [
        {"symbol": "SOL", "score": 85, "sentiment": 0.5, "category": "layer1", "price_history": [30, 32, 31, 33, 34]},
        {"symbol": "PEPE", "score": 75, "sentiment": 0.4, "category": "memecoin", "price_history": [0.00004, 0.00005, 0.000045, 0.00005, 0.000047]},
        {"symbol": "DOGE", "score": 65, "sentiment": 0.1, "category": "memecoin", "price_history": [0.07, 0.08, 0.07, 0.065, 0.06]},
    ]
    actions = apply_strategy(tokens, strategy_rules)
    print("Actions recommandées :", actions)

    for action in actions:
        execute_trade(action)

    save_log(actions)

if __name__ == "__main__":
    main()