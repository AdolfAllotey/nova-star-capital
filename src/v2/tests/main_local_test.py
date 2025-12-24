
from src.v2.monitoring.kol_tracker import track_kols
from src.v2.monitoring.whale_tracker import run_whale_tracker
from src.v2.monitoring.performance_alerts import evaluate_performance
from src.v2.monitoring.risk_controller import analyze_risk
from src.v2.reporting import generate_daily_report

def main():
    print("🧪 Démarrage test local sans envoi")

    print("📡 Test : KOLs...")
    track_kols()

    print("🐋 Test : Whales...")
    run_whale_tracker()

    print("📈 Test : Performances...")
    last_balances = {"trading": 10000, "securite": 5000, "impots": 2000}
    current_balances = {"trading": 10200, "securite": 4900, "impots": 2100}
    evaluate_performance(last_balances, current_balances)

    print("⚠️ Test : Risques...")
    analyze_risk()

    print("📊 Test : Rapport...")
    trades = [
        {"symbol": "BTC", "action": "buy", "qty": 0.1},
        {"symbol": "ETH", "action": "sell", "qty": 0.5}
    ]
    performance = {"total_pnl": 500, "roi_pct": 4.2}
    alerts = ["Test Alerte sur SOL"]

    report = generate_daily_report(trades, performance, alerts)
    print("📝 Rapport généré (non enregistré) :", report[:200], "...")

    print("✅ Fin du test local.")

if __name__ == "__main__":
    main()
