
import os
from src.v2.core.user_manager import load_users, get_user_preferences
from src.v2.core.strategy_router import apply_strategy

def main():
    print("🚀 Lancement du bot V2 - Mode Multi-Utilisateurs")

    users = load_users()
    if not users:
        print("❌ Aucun utilisateur actif trouvé.")
        return

    # Exemple de données de marché (à remplacer par vos vrais signaux)
    market_data = [
        {"token": "BTC", "volatility": 0.7, "stability_score": 90, "is_decentralized": True, "dev_commits": 50},
        {"token": "ETH", "volatility": 0.5, "stability_score": 85, "is_decentralized": True, "dev_commits": 60},
        {"token": "SOL", "volatility": 0.9, "stability_score": 60, "is_decentralized": False, "dev_commits": 30},
        {"token": "USDT", "volatility": 0.1, "stability_score": 99, "is_decentralized": False, "dev_commits": 5},
    ]

    for user in users:
        user_id = user["id"]
        print(f"👤 Traitement pour l'utilisateur : {user['name']} ({user_id})")

        prefs = get_user_preferences(user_id)
        print(f"  - Capital : {prefs['capital']}€")
        print(f"  - Niveau de risque : {prefs['risk_level']}")
        print(f"  - Tokens favoris : {prefs['preferred_tokens']}")

        result = apply_strategy(user_id, market_data)
        print(f"  ✅ Résultat stratégie : {result['strategy']}")
        for token in result["selected"]:
            print(f"     • {token['token']}")

if __name__ == "__main__":
    main()
