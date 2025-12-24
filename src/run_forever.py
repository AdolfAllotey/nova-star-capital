# src/run_forever.py

import time
from main import run_step
from social.scrape_social_data import main as run_social_scraping
from social.save_detected_tokens import main as save_tokens_main
from scoring.score_tokens import main as score_tokens_main
from scoring.sentiment_analysis import main as sentiment_main
from trading.simulate_strategy import main as simulate_trades_main
# from reporting.generate_daily_report import main as generate_report_main  # à réactiver une fois prêt

while True:
    print("\n🚀 Nouvelle itération du bot")
    run_step("Scraping social", run_social_scraping)
    run_step("Sauvegarde des tokens détectés", save_tokens_main)
    run_step("Scorage des tokens", score_tokens_main)
    run_step("Analyse de sentiment", sentiment_main)
    run_step("Simulation de stratégie", simulate_trades_main)
    # run_step("Génération du rapport quotidien", generate_report_main)

    print("⏳ Pause 1h avant prochaine exécution...\n")
    time.sleep(3600)  # 1 heure d'attente
