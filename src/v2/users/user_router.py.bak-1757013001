
import json
import os

from src.v2.config.user_mode import get_user_mode
from src.v2.users.strategy_profiles import get_profile

def route_order(decision_data):
    """
    Oriente les décisions en fonction du mode utilisateur actif (manuel ou automatique).

    Args:
        decision_data (dict): Données de trading simulées ou réelles à router.
    """
    mode = get_user_mode()
    strategy = get_profile(mode.get("profile", "equilibre"))

    if not strategy:
        print(f"❌ Profil {mode.get('profile')} introuvable. Passage en mode standard.")
        strategy = get_profile("equilibre")

    if mode.get("mode") == "manuel":
        print(f"🛑 Mode manuel activé – Aucune exécution automatique.")
        print("👉 Ordres proposés :")
        print(json.dumps(decision_data, indent=2))
        return

    if mode.get("mode") == "automatique":
        print(f"🤖 Mode auto – Application de la stratégie {strategy['name']}")
        for order in decision_data:
            adjusted_amount = order.get("amount", 0) * strategy["allocation_multiplier"]
            print(f"⏩ Ordre exécuté : {order['symbol']} - {adjusted_amount:.2f} €")

# Exemple d’utilisation
if __name__ == "__main__":
    test_orders = [
        {"symbol": "BTC", "amount": 500},
        {"symbol": "ETH", "amount": 300}
    ]
    route_order(test_orders)
