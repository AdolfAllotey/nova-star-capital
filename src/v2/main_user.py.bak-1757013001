
# src/v2/main_user.py

import time
from src.v2.core.user_manager import get_active_users
from src.v2.monitoring.kol_tracker import track_kols
from src.v2.monitoring.whale_tracker import run_whale_tracker
from src.v2.monitoring.risk_controller import analyze_risk
from src.v2.monitoring.performance_alerts import evaluate_performance
from src.v2.reporting import generate_daily_report, save_report, send_report_via_telegram
from src.v2.utils.gain_protector import protect_gains
from src.v2.core.archiver import archive_files
from src.v2.monitoring.portfolio_tracker import track_portfolio

def run_bot_for_user(user):
    print(f"👤 Exécution pour : {user['username']}")

    # Exemple : utilisation des stratégies définies
    strategies = user.get("strategies", [])

    if "kol" in strategies:
        track_kols()

    if "whale" in strategies:
        run_whale_tracker()

    # Placeholder : récupérer les soldes réels de l'utilisateur
    last_balances = {"trading": 10000, "securite": 5000, "impots": 2000}
    current_balances = {"trading": 10200, "securite": 4900, "impots": 2100}

    evaluate_performance(last_balances, current_balances)
    analyze_risk()
    track_portfolio(current_balances)

    # Placeholder : données simulées
    trades = [{"symbol": "BTC", "action": "buy", "qty": 0.1}]
    performance = {"total_pnl": 250, "roi_pct": 2.5}
    alerts = ["Signal KOL fort sur SOL"]

    report = generate_daily_report(trades, performance, alerts)
    report_path = save_report(report)

    send_report_via_telegram(report, chat_id=user["telegram_id"])
    protect_gains(current_balances)
    archive_files()

def main():
    print("🚀 Démarrage du bot multi-utilisateurs...")
    users = get_active_users()
    for user in users:
        # 🌱 Appliquer un filtre éthique si activé
        if user.get("ethical_filter"):
            from src.v2.analytics.ethical_scoring import score_token_list
            signal_data = score_token_list(signal_data)
            signal_data = [s for s in signal_data if s.get("ethical_score", 0) >= 0.5]
            print(f"🧪 {len(signal_data)} tokens retenus après filtre éthique.")

        run_bot_for_user(user)
        time.sleep(2)  # Pause légère entre chaque utilisateur

    print("✅ Tous les utilisateurs ont été traités.")

if __name__ == "__main__":
    main()
