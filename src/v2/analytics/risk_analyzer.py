import os
import json
from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("risk_analyzer")

FINAL_SCORES_PATH = "src/v2/data/scores/final_scores.json"
RISK_REPORT_PATH = "src/v2/data/risk/risk_report.json"
BLACKLIST_PATH = "src/v2/data/risk/token_blacklist.json"

def analyze_risk():
    try:
        data = load_json_file(FINAL_SCORES_PATH)
        high_risk = []
        high_potential = []
        blacklist = []

        for token in data:
            symbol = token.get("symbol")
            risk_flag = token.get("llm_risk_flag", "unknown")
            pnl = token.get("pnl_eur", 0)
            behavior = token.get("llm_behavior_score", 0)
            ethics = token.get("llm_ethics_score", 0)
            summary = token.get("llm_summary", "")
            final_score = token.get("final_score", 0)

            # Détection haut risque
            if risk_flag == "yes" or pnl < -20 or behavior < 3:
                high_risk.append({
                    "symbol": symbol,
                    "pnl_eur": pnl,
                    "llm_behavior_score": behavior,
                    "llm_risk_flag": risk_flag,
                    "summary": summary
                })
                if pnl < -50 or behavior < 2:
                    blacklist.append(symbol)

            # Détection fort potentiel
            if final_score > 8 and behavior > 7 and ethics > 7 and risk_flag == "no":
                high_potential.append({
                    "symbol": symbol,
                    "score": final_score,
                    "llm_behavior_score": behavior,
                    "llm_ethics_score": ethics,
                    "summary": summary
                })

        # Recommandation simple
        recommendation = "Avoid tokens marked as 'high risk' or with behavior score < 3. Prioritize high potential tokens with strong ethics and positive summaries."

        report = {
            "high_risk_tokens": high_risk,
            "high_potential_tokens": high_potential,
            "recommendation": recommendation
        }

        save_json_file(report, RISK_REPORT_PATH)
        if blacklist:
            save_json_file(blacklist, BLACKLIST_PATH)

        logger.info(f"Risk analysis saved to {RISK_REPORT_PATH}")
        if blacklist:
            logger.info(f"Blacklist saved to {BLACKLIST_PATH}")

    except Exception as e:
        logger.exception("Erreur lors de l'analyse des risques")

if __name__ == "__main__":
    analyze_risk()