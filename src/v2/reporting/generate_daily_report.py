import os
from datetime import datetime
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file
from pathlib import Path


# Logger centralisé
logger = get_logger("generate_daily_report")

# Dossiers et fichiers
DATA_DIR = os.getenv("DATA_DIR", "/opt/nsc/data/preprod")
DAILY_REPORT_FILE = str(Path(DATA_DIR) / "reports" / "daily_report.json")
Path(DAILY_REPORT_FILE).parent.mkdir(parents=True, exist_ok=True)
AVERAGE_SENTIMENT_FILE = str(Path(DATA_DIR) / "average_sentiment.json")
WORST_TRADES_FILE = str(Path(DATA_DIR) / "risk" / "worst_trades.json")

# Default trade simulation file (robust fallback)
TRADE_SIM_FILE = str(Path(DATA_DIR) / "trading" / "trade_simulation.json")


def _load_latest_worst_trades_summary() -> dict:
    path = str(Path(DATA_DIR) / "risk" / "worst_trades_summary.json")
    data = load_json_file(path, default={})
    if not isinstance(data, dict) or not data:
        # Fallback structuré (évite worst_trades_summary = {})
        return {
            "summary": "worst_trades_summary missing/empty; using fallback.",
            "root_causes": [],
            "tokens_to_blacklist": [],
            "suggested_rules": [],
            "metrics": {},
            "context": {"env": os.getenv("NSC_ENV", "PREPROD")},
            "llm_status": "unknown",
            "llm_error": None,
        }
    return data




def generate_daily_report(alloc=None):
    """Génère le rapport quotidien global du bot Nova Star Capital."""
    logger.info("📊 Génération du rapport quotidien...")

    # Charger les fichiers
    trades = load_json_file(TRADE_SIM_FILE, default=[])
    # Fallback: some modules write to DATA_DIR/simulation/
    if not trades:
        alt = os.path.join(DATA_DIR, "simulation", "trade_simulation.json")
        trades = load_json_file(alt, default=[])

    worst_trades = load_json_file(WORST_TRADES_FILE, default=[])
    worst_trades_summary = _load_latest_worst_trades_summary()

    # average_sentiment: PRIMARY FIRST, then fallback paths
    average_sentiment = {}
    try:
        primary = Path(AVERAGE_SENTIMENT_FILE)
        if primary.exists():
            average_sentiment = load_json_file(str(primary), default={})
        else:
            fallbacks = [
                str(Path(DATA_DIR) / 'analysis' / 'average_sentiment.json'),
                str(Path(DATA_DIR) / 'reports' / 'average_sentiment.json'),
                str(Path(DATA_DIR) / 'sentiment' / 'average_sentiment.json'),
            ]
            used_fb = None
            for fb in fallbacks:
                fb_path = Path(fb)
                if fb_path.exists():
                    used_fb = fb
                    average_sentiment = load_json_file(str(fb_path), default={})
                    logger.warning(f'Using fallback average_sentiment file: {fb}')
                    break

            # If we used a fallback, create the primary file for next runs
            if used_fb is not None:
                try:
                    src = Path(used_fb)
                    primary.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
                    logger.info(f'Created primary average_sentiment file from fallback: {AVERAGE_SENTIMENT_FILE}')
                except Exception as e:
                    logger.warning(f'Could not create primary average_sentiment file {AVERAGE_SENTIMENT_FILE}: {e}')
            else:
                logger.warning(f'average_sentiment file not found (expected {AVERAGE_SENTIMENT_FILE}); using {{}}')
    except Exception as e:
        logger.warning(f'average_sentiment load failed; using {{}}: {e}')

    # Gestion du cas où sentiment est une liste
    if isinstance(average_sentiment, list):
        logger.warning("⚠️ Format inattendu pour average_sentiment.json, conversion en dict vide.")
        average_sentiment = {}

    # Création du rapport
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "trade_count": (len(trades) if isinstance(trades, list) else 0),
        "worst_trade_count": (len(worst_trades) if isinstance(worst_trades, list) else 0),
        "average_sentiment": average_sentiment,
        "worst_trades_summary": worst_trades_summary
    }

    # Sauvegarde du rapport
    save_json_file(DAILY_REPORT_FILE, report)
    logger.info(f"✅ Rapport quotidien généré : {DAILY_REPORT_FILE}")

    return report


if __name__ == "__main__":
    generate_daily_report()