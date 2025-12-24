import os

def run_dashboard():
    while True:
        print("\n📊 MENU DASHBOARD")
        print("1️⃣  Lancer optimisation batch EMA & RSI")
        print("2️⃣  Comparer EMA vs RSI (CSV + graphique)")
        print("3️⃣  Extraire meilleures stratégies")
        print("4️⃣  Visualisation interactive (Plotly)")
        print("5️⃣  Générer rapport PDF global")
        print("6️⃣  Lancer stratégie Shitcoin (via config.json)")
        print("7️⃣  Ouvrir l'interface Web Streamlit")
        print("8️⃣  Exécution automatique complète (batch > analyse > PDF)")
        print("9️⃣  Lancer scraping + backtest Telegram")
        print("🔟  Lancer scraping + backtest Reddit")
        print("0️⃣  Quitter")

        choice = input("👉 Choix : ").strip()

        if choice == "1":
            os.system("python3 src/backtester/run_batch_optimization.py")

        elif choice == "2":
            os.system("python3 src/backtester/run_batch_comparison.py")
            os.system("python3 src/backtester/visualize_global_comparison.py")

        elif choice == "3":
            os.system("python3 src/backtester/extract_best_strategies.py")
            os.system("python3 src/backtester/visualize_best_strategies.py")

        elif choice == "4":
            os.system("python3 src/backtester/visualize_best_strategies_interactive.py")

        elif choice == "5":
            os.system("python3 src/backtester/generate_report_pdf.py")

        elif choice == "6":
            os.system("python3 src/backtester/backtest_runner.py")

        elif choice == "7":
            os.system("sh launch_streamlit.command")

        elif choice == "8":
            os.system("python3 src/backtester/run_batch_optimization.py")
            os.system("python3 src/backtester/extract_best_strategies.py")
            os.system("python3 src/backtester/generate_report_pdf.py")

        elif choice == "9":
            print("\n📨 Lancement scraping + backtest Telegram...")
            os.system("python3 src/social/telegram_scraper.py")
            os.system("python3 src/backtester/run_telegram_shitcoin_backtests.py")

        elif choice == "10":
            print("\n👽 Lancement scraping + backtest Reddit...")
            os.system("python3 src/social/reddit_scraper.py")
            os.system("python3 src/backtester/run_reddit_shitcoin_backtests.py")

        elif choice == "0":
            print("👋 À bientôt !")
            break

        else:
            print("❌ Option invalide. Réessaie.")

if __name__ == "__main__":
    run_dashboard()